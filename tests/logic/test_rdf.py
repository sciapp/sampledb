# coding: utf-8
"""

"""

from lxml import etree
from urllib.parse import urlparse

import pytest

import sampledb
from sampledb.logic import actions, comments, objects, rdf


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="user@example.org", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def other_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Other User", email="user@example.org", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def test_generate_rdf(flask_server, user, other_user):
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        description='',
        instrument_id=None
    )
    data = {'name': {'_type': 'text', 'text': 'Example Object'}}
    object = objects.create_object(user_id=user.id, action_id=action.id, data=data)

    comments.create_comment(object.id, other_user.id, 'Example Comment')

    objects.update_object(object.id, data, user.id)

    objects.update_object(object.id, data, other_user.id)

    flask_server.app.config['SERVER_NAME'] = urlparse(flask_server.base_url).netloc
    with flask_server.app.app_context():
        rdf_document = rdf.generate_rdf(user.id, object.id)

    etree.register_namespace('dcterms', 'http://purl.org/dc/terms/')
    et = etree.fromstring(rdf_document)

    assert next(et.iter('{*}title')).text == 'Example Object'
    assert next(et.iter('{*}identifier')).text == f'{flask_server.base_url}objects/{object.id}'
    creators = list(et.iter('{*}creator'))
    assert len(creators) == 2
    assert creators[0][0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about') == f'{flask_server.base_url}users/{user.id}'
    assert creators[0][0][0].text == user.name
    assert creators[1][0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about') == f'{flask_server.base_url}users/{other_user.id}'
    assert creators[1][0][0].text == other_user.name
    contributors = list(et.iter('{*}contributor'))
    assert len(contributors) == 0
    versions = list(et.iter('{*}hasVersion'))
    assert len(versions) == 3
    assert versions[0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource') == f'{flask_server.base_url}objects/{object.id}/versions/0'
    assert versions[1].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource') == f'{flask_server.base_url}objects/{object.id}/versions/1'
    assert versions[2].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource') == f'{flask_server.base_url}objects/{object.id}/versions/2'
    is_version_of = list(et.iter('{*}isVersionOf'))
    assert len(is_version_of) == 0

    flask_server.app.config['SERVER_NAME'] = urlparse(flask_server.base_url).netloc
    with flask_server.app.app_context():
        rdf_document = rdf.generate_rdf(user.id, object.id, 1)

    etree.register_namespace('dcterms', 'http://purl.org/dc/terms/')
    et = etree.fromstring(rdf_document)

    assert next(et.iter('{*}title')).text == 'Example Object'
    assert next(et.iter('{*}identifier')).text == f'{flask_server.base_url}objects/{object.id}/versions/1'
    creators = list(et.iter('{*}creator'))
    assert len(creators) == 1
    assert creators[0][0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about') == f'{flask_server.base_url}users/{user.id}'
    assert creators[0][0][0].text == user.name
    contributors = list(et.iter('{*}contributor'))
    assert len(contributors) == 1
    assert contributors[0][0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about') == f'{flask_server.base_url}users/{other_user.id}'
    assert contributors[0][0][0].text == other_user.name
    versions = list(et.iter('{*}hasVersion'))
    assert len(versions) == 0
    is_version_of = list(et.iter('{*}isVersionOf'))
    assert len(is_version_of) == 1
    assert is_version_of[0].get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource') == f'{flask_server.base_url}objects/{object.id}'
