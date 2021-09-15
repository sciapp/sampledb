"""
This module offers functions for exporting SampleDB information to a Dataverse
instance with support for the Processing Metadata from the EngMeta schemas
(see: https://www.izus.uni-stuttgart.de/fokus/engmeta).

Some basic information is exported to the default Citation Metadata block and
the process-specific metadata is exported to the Method Parameters fields of
the Processing Metadata block.
"""

import datetime
import json
import typing
from urllib.parse import urlencode

import flask
import requests

from .. import db
from .units import prettify_units
from . import actions, datatypes, object_log, users, objects, errors, object_permissions, files, settings, instrument_translations, languages
from ..models import DataverseExport


DATAVERSE_TIMEOUT = 30


def flatten_metadata(
        metadata: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]],
        path: typing.Optional[typing.List[typing.Union[str, int]]] = None
) -> typing.Generator[typing.Tuple[typing.Dict[str, typing.Any], typing.List[typing.Union[str, int]]], None, None]:
    """
    Convert nested object data to a generator yielding the property data and path.

    :param metadata: the nested object data
    :param path: the path to start at, or None
    :return: the generator for property data and path
    """
    if path is None:
        path = []
    if isinstance(metadata, list):
        yield from _flatten_metadata_array(metadata, path)
    elif isinstance(metadata, dict) and '_type' not in metadata:
        yield from _flatten_metadata_object(metadata, path)
    else:
        yield metadata, path


def _flatten_metadata_array(
        metadata: typing.List[typing.Any],
        path: typing.List[typing.Union[str, int]]
) -> typing.Generator[typing.Tuple[typing.Dict[str, typing.Any], typing.List[typing.Union[str, int]]], None, None]:
    for index, value in enumerate(metadata):
        yield from flatten_metadata(value, path + [index])


def _flatten_metadata_object(
        metadata: typing.Dict[str, typing.Any],
        path: typing.List[typing.Union[str, int]]
) -> typing.Generator[typing.Tuple[typing.Dict[str, typing.Any], typing.List[typing.Union[str, int]]], None, None]:
    for key, value in metadata.items():
        yield from flatten_metadata(value, path + [key])


def _translations_to_str(
        content: typing.Optional[typing.Union[str, typing.Dict[str, str]]]
) -> str:
    if isinstance(content, dict):
        if len(content) == 1:
            content = content[list(content)[0]]
        else:
            content = json.dumps(content)
    return content


def get_title_for_property(
        path: typing.List[str],
        schema: typing.Dict[str, typing.Any]
) -> str:
    """
    Return the title path for a given property.

    The title path consists of the individual titles or indices, joined by the
    rightwards arrow symbol.

    :param path: the path to a property
    :param schema: the object schema
    :return: the title path
    """
    try:
        subschema = schema
        title_path = []
        for key in path:
            if isinstance(key, str):
                subschema = subschema['properties'][key]
                if isinstance(subschema['title'], dict):
                    title_path.append(subschema['title'].get('en', subschema['title']))
                else:
                    title_path.append(subschema['title'])
            else:
                subschema = subschema['items']
                title_path.append(key)
    except Exception:
        title_path = path
    return ' → '.join(map(str, title_path))


def get_property_export_default(
        path: typing.List[str],
        schema: typing.Dict[str, typing.Any]
) -> bool:
    """
    Return whether dataverse_export is set to True in the schema of a property.

    :param path: the path to a property
    :param schema: the object schema
    :return: the value of dataverse_export, or False if it is not set
    """
    if path == ['name']:
        return True
    try:
        subschema = schema
        for key in path:
            if isinstance(key, str):
                subschema = subschema['properties'][key]
            else:
                subschema = subschema['items']
        return subschema.get('dataverse_export', False)
    except Exception:
        return False


def _convert_metadata_to_process(metadata, schema, user_id, property_whitelist):
    fields = []
    for value, path in flatten_metadata(metadata):
        if path not in property_whitelist:
            continue
        title = get_title_for_property(path, schema)
        units = ''
        magnitude = ''
        text_value = ''
        symbol = ''
        if value['_type'] == 'quantity':
            units = prettify_units(value['units'])
            if units == '1':
                # dimensionless quantities with a factor of 1 do not need units
                units = ''
            magnitude = f"{datatypes.Quantity.from_json(value).magnitude:g}"
        elif value['_type'] == 'text':
            text_value = _translations_to_str(datatypes.Text.from_json(value).text)
        elif value['_type'] == 'bool':
            text_value = str(datatypes.Boolean.from_json(value).value)
        elif value['_type'] == 'datetime':
            text_value = datatypes.DateTime.from_json(value).utc_datetime.isoformat()
        elif value['_type'] == 'hazards':
            hazard_names = {
                1: 'Explosive',
                2: 'Flammable',
                3: 'Oxidizing',
                4: 'Compressed Gas',
                5: 'Corrosive',
                6: 'Toxic',
                7: 'Harmful',
                8: 'Health Hazard',
                9: 'Environmental Hazard'
            }
            text_value = ', '.join(hazard_names[hazard_id] for hazard_id in sorted(value['hazards']))
        elif value['_type'] == 'tags':
            # tags are handled separately via the keywords in Citation Metadata
            continue
        elif value['_type'] == 'user':
            try:
                text_value = users.get_user(value['user_id']).name
            except errors.UserDoesNotExistError:
                text_value = 'Unknown'
        elif value['_type'] in ('sample', 'measurement', 'object_reference'):
            object_id = value['object_id']
            if object_permissions.Permissions.READ in object_permissions.get_user_object_permissions(object_id, user_id):
                object_name = _translations_to_str(objects.get_object(object_id).data.get('name', {}).get('text'))
            else:
                object_name = None
            if object_name:
                text_value = f"{object_name} (#{object_id})"
            else:
                text_value = f"#{object_id}"
        else:
            continue
        fields.append({
            'processMethodsParName': {
                'typeName': 'processMethodsParName',
                'multiple': False,
                'typeClass': 'primitive',
                'value': title
            },
            'processMethodsParUnit': {
                'typeName': 'processMethodsParUnit',
                'multiple': False,
                'typeClass': 'primitive',
                'value': units
            },
            'processMethodsParValue': {
                'typeName': 'processMethodsParValue',
                'multiple': False,
                'typeClass': 'primitive',
                'value': magnitude
            },
            'processMethodsParTextValue': {
                'typeName': 'processMethodsParTextValue',
                'multiple': False,
                'typeClass': 'primitive',
                'value': text_value
            },
            'processMethodsParSymbol': {
                'typeName': 'processMethodsParSymbol',
                'multiple': False,
                'typeClass': 'primitive',
                'value': symbol
            }
        })
    return fields


def upload_object(
        object_id: int,
        user_id: int,
        server_url: str,
        api_token: str,
        dataverse: str,
        property_whitelist: typing.Optional[typing.Sequence[typing.List[typing.Union[str, int]]]] = None,
        file_id_whitelist: typing.Sequence[int] = (),
        tag_whitelist: typing.Sequence[str] = ()
) -> typing.Tuple[bool, typing.Union[str, typing.Dict[str, typing.Any]]]:
    """
    Uploads object information and files to a given Dataverse.

    Only properties and non-hidden files included in the provided whitelists
    will be exported, aside from the name and auxiliary information such as
    the deposition date and the list of authors.

    :param object_id: the ID of an existing object to upload
    :param user_id: the ID of the uploading user
    :param server_url: the base URL of a Dataverse server
    :param api_token: an API token for the Dataverse instance
    :param dataverse: the Dataverse to upload to
    :param property_whitelist: a list of property paths to be uploaded
    :param file_id_whitelist: a list of file IDs to be uploaded
    :param tag_whitelist: a list of tags to be set as keywords
    :return: whether or not the upload was successful and the Dataverse url
        or a dictionary containing additional information
    """
    if property_whitelist is None:
        property_whitelist = [['name']]

    object = objects.get_object(object_id)

    depositor = users.get_user(user_id)
    date_of_deposit = datetime.date.today()

    sampledb_metadata = object.data
    schema = object.schema

    action = actions.get_action(object.action_id)
    if action.instrument_id:
        instrument_name = instrument_translations.get_instrument_translation_for_instrument_in_language(
            instrument_id=action.instrument_id,
            language_id=languages.Language.ENGLISH,
            use_fallback=True
        ).name
    else:
        instrument_name = None

    author_ids = set()
    for entry in object_log.get_object_log_entries(object.id, user_id):
        if entry.type in {
            object_log.ObjectLogEntryType.CREATE_BATCH,
            object_log.ObjectLogEntryType.CREATE_OBJECT,
            object_log.ObjectLogEntryType.EDIT_OBJECT,
            object_log.ObjectLogEntryType.RESTORE_OBJECT_VERSION,
        }:
            author_ids.add(entry.user_id)

    authors = [
        users.get_user(author_id)
        for author_id in author_ids
    ]
    authors.sort(key=lambda author: author.name)

    tags = set()
    for property in object.data.values():
        if '_type' in property and property['_type'] == 'tags':
            for tag in property['tags']:
                if tag in tag_whitelist:
                    tags.add(tag)
    tags = list(tags)
    tags.sort()

    author_metadata = []

    for author in authors:
        author_metadata.append({
            'authorName': {
                'typeName': 'authorName',
                'multiple': False,
                'typeClass': 'primitive',
                'value': author.name
            }
        })
        if author.orcid:
            author_metadata[-1]["authorIdentifierScheme"] = {
                "typeName": "authorIdentifierScheme",
                "multiple": False,
                "typeClass": "controlledVocabulary",
                "value": "ORCID"
            }
            author_metadata[-1]["authorIdentifier"] = {
                "typeName": "authorIdentifier",
                "multiple": False,
                "typeClass": "primitive",
                "value": author.orcid
            }
        if author.affiliation:
            author_metadata[-1]["authorAffiliation"] = {
                "typeName": "authorAffiliation",
                "multiple": False,
                "typeClass": "primitive",
                "value": author.affiliation
            }

    method_parameters = _convert_metadata_to_process(sampledb_metadata, schema, user_id, property_whitelist)

    citation_metadata = {
        'displayName': 'Citation Metadata',
        'fields': [
            {
                'typeName': 'title',
                'multiple': False,
                'typeClass': 'primitive',
                'value': sampledb_metadata['name']['text'].get('en', json.dumps(sampledb_metadata['name']['text'])) if isinstance(sampledb_metadata['name']['text'], dict) else json.dumps(sampledb_metadata['name']['text'])
            },
            {
                'typeName': 'alternativeURL',
                'multiple': False,
                'typeClass': 'primitive',
                'value': flask.url_for('frontend.object', object_id=object_id, _external=True)
            },
            {
                'typeName': 'otherId',
                'multiple': True,
                'typeClass': 'compound',
                'value': [
                    {
                        'otherIdAgency': {
                            'typeName': 'otherIdAgency',
                            'multiple': False,
                            'typeClass': 'primitive',
                            'value': flask.current_app.config['SERVICE_NAME']
                        },
                        'otherIdValue': {
                            'typeName': 'otherIdValue',
                            'multiple': False,
                            'typeClass': 'primitive',
                            'value': str(object_id)
                        }
                    }
                ]
            },
            {
                'typeName': 'author',
                'multiple': True,
                'typeClass': 'compound',
                'value': author_metadata
            },
            {
                'typeName': 'datasetContact',
                'multiple': True,
                'typeClass': 'compound',
                'value': [
                    {
                        'datasetContactName': {
                            'typeName': 'datasetContactName',
                            'multiple': False,
                            'typeClass': 'primitive',
                            'value': depositor.name
                        },
                        'datasetContactEmail': {
                            'typeName': 'datasetContactEmail',
                            'multiple': False,
                            'typeClass': 'primitive',
                            'value': depositor.email
                        }
                    }
                ]
            },
            {
                'typeName': 'dsDescription',
                'multiple': True,
                'typeClass': 'compound',
                'value': [
                    {
                        'dsDescriptionValue': {
                            'typeName': 'dsDescriptionValue',
                            'multiple': False,
                            'typeClass': 'primitive',
                            'value': f'Dataset exported from {flask.current_app.config["SERVICE_NAME"]}.'
                        }
                    }
                ]
            },
            {
                'typeName': 'subject',
                'multiple': True,
                'typeClass': 'controlledVocabulary',
                'value': ['Other']
            },
            {
                'typeName': 'depositor',
                'multiple': False,
                'typeClass': 'primitive',
                'value': depositor.name
            },
            {
                'typeName': 'dateOfDeposit',
                'multiple': False,
                'typeClass': 'primitive',
                'value': date_of_deposit.strftime('%Y-%m-%d')
            }
        ]
    }

    if tags:
        citation_metadata['fields'].append({
            "typeName": "keyword",
            "multiple": True,
            "typeClass": "compound",
            "value": [
                {
                    "keywordValue": {
                        "typeName": "keywordValue",
                        "multiple": False,
                        "typeClass": "primitive",
                        "value": tag
                    }
                } for tag in tags
            ]
        })

    process_metadata = {
        'displayName': 'Process Metadata',
        'fields': []
    }

    if method_parameters:
        process_metadata['fields'].append({
            'typeName': 'processMethodsPar',
            'multiple': True,
            'typeClass': 'compound',
            'value': method_parameters
        })

    if instrument_name:
        process_metadata['fields'].append({
            "typeName": "processInstru",
            "multiple": True,
            "typeClass": "compound",
            "value": [
                {
                    "processInstruName": {
                        "typeName": "processInstruName",
                        "multiple": False,
                        "typeClass": "primitive",
                        "value": instrument_name
                    }
                }
            ]
        })

    metadata_blocks = {
        'citation': citation_metadata,
        'process': process_metadata
    }

    dataverse_metadata = {
        'datasetVersion': {
            'metadataBlocks': metadata_blocks
        }
    }

    try:
        r = requests.post(
            f'{server_url}/api/v1/dataverses/{dataverse}/datasets/',
            headers={
                'X-Dataverse-key': api_token
            },
            allow_redirects=False,
            json=dataverse_metadata,
            timeout=DATAVERSE_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.DataverseNotReachableError()
    try:
        result = r.json()
        if r.status_code == 201 and result['status'] == 'OK':
            persistent_id = result['data']['persistentId']
            dataverse_url = f'{server_url}/dataset.xhtml?{urlencode({"persistentId": persistent_id})}'
            dataverse_export = DataverseExport(object_id, dataverse_url, user_id)
            db.session.add(dataverse_export)
            db.session.commit()
            object_log.export_to_dataverse(user_id, object_id, dataverse_url)
            _upload_files_to_dataset(server_url, api_token, persistent_id, object_id, file_id_whitelist)
            return True, dataverse_url
        return False, r.json()
    except Exception:
        return False, {}


def _upload_files_to_dataset(
    server_url: str,
    api_token: str,
    persistent_id: str,
    object_id: int,
    file_id_whitelist: typing.Sequence[int]
) -> None:
    """
    Upload files for an object to the given Dataverse dataset.

    Only non-hidden files with IDs from the file_id_whitelist and in local
    storage will be uploaded. Failed file uploads will be ignored

    :param server_url: the base URL of a Dataverse server
    :param api_token: an API token for the Dataverse instance
    :param persistent_id: the Dataverse ID of the dataset
    :param object_id: the ID of the corresponding object
    :param file_id_whitelist: a list of file IDs to be uploaded
    :raise errors.DataverseNotReachableError: if there was an error during
        communication with the Dataverse API
    """
    for file in files.get_files_for_object(object_id):
        if file.id not in file_id_whitelist:
            continue
        if file.is_hidden:
            continue
        if file.data.get('storage') in {'local', 'database'}:
            file_name = file.original_file_name
            file_content = file.open(read_only=True).read()
            if file.title and file.description:
                file_description = file.title + '\n\n' + file.description
            elif file.title:
                file_description = file.title
            elif file.description:
                file_description = file.description
            else:
                file_description = ''
            try:
                requests.post(
                    f'{server_url}/api/datasets/:persistentId/add',
                    data={
                        'jsonData': json.dumps({
                            'description': file_description,
                            'categories': []
                        })
                    },
                    files={
                        'file': (file_name, file_content),
                    },
                    params={
                        'persistentId': persistent_id
                    },
                    headers={
                        'X-Dataverse-key': api_token
                    },
                    timeout=DATAVERSE_TIMEOUT
                )
            except requests.exceptions.RequestException:
                # ignore failed file uploads
                pass


def list_dataverses(
        server_url: str,
        api_token: str,
        dataverse: str
) -> typing.List[typing.Tuple[int, typing.Dict[str, typing.Any]]]:
    """
    Return information on a dataverse and its children.

    For each dataverse, the list returned by this function contains the degree
    by which it is descended from the given dataverse, and a dictionary
    containing their ID and title.

    :param server_url: the base URL of a Dataverse server
    :param api_token: an API token for the Dataverse instance
    :param dataverse: the Dataverse to get information for
    :return: a list with information on dataverses
    :raise errors.DataverseNotReachableError: if there was an error during
        communication with the Dataverse API
    """
    dataverses = []

    dataverses_with_children = [
        (1, dataverse)
        for dataverse in _list_dataverses_nested(server_url, api_token, dataverse)
    ]

    while dataverses_with_children:
        level, dataverse_with_children = dataverses_with_children.pop(0)
        dataverses.append((level, {
            'id': dataverse_with_children.get('id'),
            'title': dataverse_with_children.get('title')
        }))
        for child_dataverse in reversed(dataverse_with_children['child_dataverses']):
            dataverses_with_children.insert(0, (level + 1, child_dataverse))

    return dataverses


def get_dataverse_info(
        server_url: str,
        api_token: str,
        dataverse: str
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    """
    Return information on a given Dataverse.

    :param server_url: the base URL of a Dataverse server
    :param api_token: an API token for the Dataverse instance
    :param dataverse: the Dataverse to get information for
    :return: a dictionary containing the Dataverse ID and title, or None
    :raise errors.DataverseNotReachableError: if there was an error during
        communication with the Dataverse API
    """
    try:
        r = requests.get(
            f'{server_url}/api/v1/dataverses/{dataverse}',
            headers={
                'X-Dataverse-key': api_token
            },
            allow_redirects=False,
            timeout=DATAVERSE_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.DataverseNotReachableError()
    if r.status_code != 200:
        return None
    try:
        result = r.json()
        if result.get('status') != 'OK':
            return None
        return {
            'id': result['data']['id'],
            'title': result['data']['name']
        }
    except Exception:
        return None


def _list_dataverses_nested(
        server_url: str,
        api_token: str,
        dataverse: str
) -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Return information on Dataverses within a given Dataverse.

    :param server_url: the base URL of a Dataverse server
    :param api_token: an API token for the Dataverse instance
    :param dataverse: the root Dataverse to search in
    :return: a list of dictionaries containing the Dataverse information
    :raise errors.DataverseNotReachableError: if there was an error during
        communication with the Dataverse API
    """
    if dataverse is None:
        return []
    try:
        r = requests.get(
            f'{server_url}/api/v1/dataverses/{dataverse}/contents',
            headers={
                'X-Dataverse-key': api_token
            },
            allow_redirects=False,
            timeout=DATAVERSE_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.DataverseNotReachableError()
    if r.status_code != 200:
        return []
    try:
        result = r.json()
    except Exception:
        return []
    if result.get('status') != 'OK':
        return []
    child_dataverses = []
    for entry in result.get('data', ()):
        if entry.get('type') == "dataverse":
            if 'id' not in entry or 'title' not in entry:
                continue
            child_dataverses.append({
                'id': entry.get('id'),
                'title': entry.get('title'),
                'child_dataverses': _list_dataverses_nested(server_url, api_token, entry.get('id'))
            })
    return child_dataverses


def get_dataverse_url(object_id: int) -> typing.Optional[str]:
    """
    Return the URL for an object in a Dataverse instance.

    :param object_id: the ID of an existing object
    :return: the URL or None
    """
    dataverse_export = DataverseExport.query.filter_by(object_id=object_id).first()
    if dataverse_export is None:
        return None
    return dataverse_export.dataverse_url


def get_user_valid_api_token(server_url: str, user_id: int) -> typing.Optional[str]:
    """
    Return whether a user has a valid API token for a given Dataverse instance.

    :param server_url: the base URL of the Dataverse server
    :param user_id: the ID of an existing user
    :return: a valid API token stored for the user, or None
    :raise errors.UserDoesNotExistError: if not user with the given user ID
        exists
    :raise errors.DataverseNotReachableError: if there was an error during
        communication with the Dataverse API
    """
    api_token = settings.get_user_settings(user_id)['DATAVERSE_API_TOKEN']
    if not api_token:
        # make sure the user even exists
        users.get_user(user_id)
        return None
    if not is_api_token_valid(server_url, api_token):
        return None
    return api_token


def is_api_token_valid(server_url: str, api_token: str) -> bool:
    """
    Return whether an API token is valid for a given Dataverse instance.

    :param server_url: the base URL of the Dataverse server
    :param api_token: the API token to validate
    :return: whether or not the API token is valid
    :raise errors.DataverseNotReachableError: if there was an error during
        communication with the Dataverse API
    """
    # check basic API token structure
    if not all(c in '0123456789abcdef-' for c in api_token):
        return False
    parts = api_token.split('-')
    if len(parts) != 5:
        return False
    if [len(part) for part in parts] != [8, 4, 4, 4, 12]:
        return False
    # check whether the API token can actually be used
    try:
        r = requests.get(
            f'{server_url}/api/v1/users/token',
            headers={
                'X-Dataverse-key': api_token
            },
            allow_redirects=False,
            timeout=DATAVERSE_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.DataverseNotReachableError()
    if r.status_code != 200:
        return False
    return True


def dataverse_has_required_metadata_blocks(server_url: str, api_token: str, dataverse: str) -> bool:
    """
    Return whether a Dataverse has the metadata blocks required for export.

    :param server_url: the base URL of a Dataverse server
    :param api_token: an API token for the Dataverse instance
    :param dataverse: the Dataverse to check
    :return: whether the Dataverse has the required metadata blocks
    :raise errors.DataverseNotReachableError: if there was an error during
        communication with the Dataverse API
    """
    try:
        r = requests.get(
            f'{server_url}/api/v1/dataverses/{dataverse}/metadatablocks',
            headers={
                'X-Dataverse-key': api_token
            },
            allow_redirects=False,
            timeout=DATAVERSE_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.DataverseNotReachableError()
    if r.status_code != 200:
        # user might not even be allowed to access the Dataverse
        return False
    try:
        result = r.json()
        if result['status'] != 'OK':
            return False
        metadata_blocks = set()
        for metadata_block in result['data']:
            metadata_blocks.add(metadata_block['name'])
    except Exception:
        return False
    required_metadata_blocks = {'citation', 'process'}
    return all(
        metadata_block in metadata_blocks
        for metadata_block in required_metadata_blocks
    )
