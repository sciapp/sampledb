# coding: utf-8
"""
Dublin Core metadata in RDF/XML format
"""

import typing

import flask
import jinja2

from . import objects, object_log, users
from ..frontend.utils import get_translated_text

RDF_TEMPLATE = jinja2.Template("""<?xml version="1.0"?>
<rdf:RDF
xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns:dcterms="http://purl.org/dc/terms/"
xmlns:foaf="http://xmlns.com/foaf/0.1/"
>
  <rdf:Description xml:lang="en" rdf:about="{{ object_url }}">
    <dcterms:identifier>{{ object_url }}</dcterms:identifier>
    {% if object_name_is_str %}
    <dcterms:title>{{ object_name }}</dcterms:title>
    {% else %}
    <dcterms:title>{{ get_translated_text(object_name, 'en') }}</dcterms:title>
      {% for language_code in object_name %}
        {% if language_code != 'en' and object_name[language_code] %}
    <dcterms:alternative xml:lang="{{ language_code }}">{{ object_name[language_code] }}</dcterms:alternative>
        {% endif %}
      {% endfor %}
    {% endif %}
    <dcterms:created>{{ created.isoformat() }}</dcterms:created>
    <dcterms:modified>{{ modified.isoformat() }}</dcterms:modified>

{% for user in creators %}
    <dcterms:creator>
      <foaf:Person rdf:about="{{ user['url'] }}">
        <foaf:name>{{ user['name'] }}</foaf:name>
      </foaf:Person>
    </dcterms:creator>
{% endfor %}

{% for user in contributors %}
    <dcterms:contributor>
      <foaf:Person rdf:about="{{ user['url'] }}">
        <foaf:name>{{ user['name'] }}</foaf:name>
      </foaf:Person>
    </dcterms:contributor>
{% endfor %}

{% for version_url in version_urls %}
    <dcterms:hasVersion rdf:resource="{{ version_url }}" />
{% endfor %}

{% if current_object_url %}
    <dcterms:isVersionOf rdf:resource="{{ current_object_url }}" />
{% endif %}
  </rdf:Description>
</rdf:RDF>
""")


def generate_rdf(user_id: int, object_id: int, version_id: typing.Optional[int] = None) -> str:
    """
    Generate an XML file for an object.

    The file will contain an RDF description for an object using Dublin Core metadata.

    :param user_id: the ID of an existing user
    :param object_id: the ID of the existing object
    :param version_id: the ID of the object's existing version
    :return:
    :raise errors.UserDoesNotExistError: when no user with the given ID exists
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.ObjectVersionDoesNotExistError: when an object with the
        given object ID exists, but does not have a version with the given
        version ID
    """

    object = objects.get_object(object_id, version_id)

    log_entries = object_log.get_object_log_entries(object.id, user_id)

    creation_datetime = object.utc_datetime
    modification_datetime = object.utc_datetime

    creator_ids = []
    contributor_ids = []
    for entry in reversed(log_entries):
        if entry.utc_datetime > modification_datetime:
            modification_datetime = entry.utc_datetime
        if entry.type in {
            object_log.ObjectLogEntryType.CREATE_BATCH,
            object_log.ObjectLogEntryType.CREATE_OBJECT,
            object_log.ObjectLogEntryType.EDIT_OBJECT,
            object_log.ObjectLogEntryType.RESTORE_OBJECT_VERSION,
        }:
            if entry.user_id not in creator_ids:
                creator_ids.append(entry.user_id)
            if entry.type in {
                object_log.ObjectLogEntryType.CREATE_OBJECT,
                object_log.ObjectLogEntryType.CREATE_BATCH
            }:
                creation_datetime = entry.utc_datetime
                if version_id == 0:
                    break

            if entry.type in {
                object_log.ObjectLogEntryType.EDIT_OBJECT,
                object_log.ObjectLogEntryType.RESTORE_OBJECT_VERSION,
            } and entry.data['version_id'] == version_id:
                break
        else:
            if entry.user_id not in contributor_ids:
                contributor_ids.append(entry.user_id)

    creators = [
        users.get_user(user_id)
        for user_id in creator_ids
    ]

    contributors = [
        users.get_user(user_id)
        for user_id in contributor_ids
        if user_id not in creator_ids
    ]

    if version_id is None:
        object_url = flask.url_for(
            'frontend.object',
            object_id=object_id,
            _external=True
        )
        version_urls = [
            flask.url_for(
                'frontend.object_version',
                object_id=object_id,
                version_id=other_version_id,
                _external=True
            )
            for other_version_id in range(object.version_id + 1)
        ]
        current_object_url = None
    else:
        object_url = flask.url_for(
            'frontend.object_version',
            object_id=object_id,
            version_id=version_id,
            _external=True
        )
        version_urls = []
        current_object_url = flask.url_for(
            'frontend.object',
            object_id=object_id,
            _external=True
        )

    object_name = object.data.get('name', {}).get('text', 'Unnamed Object')

    return RDF_TEMPLATE.render(
        object_url=object_url,
        object_name=object_name,
        object_name_is_str=isinstance(object_name, str),
        created=creation_datetime,
        modified=modification_datetime,
        creators=[
            {
                'name': user.name,
                'url': flask.url_for('frontend.user_profile', user_id=user.id, _external=True)
            }
            for user in creators
        ],
        contributors=[
            {
                'name': user.name,
                'url': flask.url_for('frontend.user_profile', user_id=user.id, _external=True)
            }
            for user in contributors
        ],
        version_urls=version_urls,
        current_object_url=current_object_url,
        get_translated_text=get_translated_text
    )
