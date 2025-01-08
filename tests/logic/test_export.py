# coding: utf-8
"""

"""

import io
import json
import os.path
import sys
import tarfile
import tempfile
import zipfile

import pytest
import rocrate_validator.models
import rocrate_validator.services
import rocrate_validator.utils
from rocrate.rocrate import ROCrate

import sampledb
from sampledb.models import User
from sampledb.logic import export, objects, actions, files


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def set_up_state(user: User):
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
        instrument_id=None
    )
    sampledb.logic.action_translations.set_action_translation(
        action_id=action.id,
        language_id=sampledb.logic.languages.Language.ENGLISH,
        name='Example Action',
        description=''
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    action2 = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
        instrument_id=None
    )
    sampledb.logic.action_translations.set_action_translation(
        action_id=action2.id,
        language_id=sampledb.logic.languages.Language.ENGLISH,
        name='Irrelevant Action',
        description=''
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action2.id, sampledb.models.Permissions.READ)
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    object = objects.create_object(user_id=user.id, action_id=action.id, data=data)
    def save_content(file): file.write("This is a test file.".encode('utf-8'))
    files.create_database_file(object.id, user.id, "test.txt", save_content)
    files.create_url_file(object.id, user.id, "https://example.com")

    instrument = sampledb.logic.instruments.create_instrument(
        users_can_view_log_entries=True
    )
    sampledb.logic.instrument_translations.set_instrument_translation(
        instrument_id=instrument.id,
        language_id=sampledb.logic.languages.Language.ENGLISH,
        name='Example Instrument',
        description='Example Instrument Description'
    )
    category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title="Category",
        theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
    )
    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry Text",
        category_ids=[category.id]
    )
    sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
        instrument_log_entry_id=log_entry.id,
        file_name="example.txt",
        content=b'Example Content'
    )
    sampledb.logic.instrument_log_entries.create_instrument_log_object_attachment(
        instrument_log_entry_id=log_entry.id,
        object_id=object.id
    )


def validate_data(data):
    # remove datetimes before comparison
    del data['objects'][0]['versions'][0]['utc_datetime']
    del data['objects'][0]['files'][0]['utc_datetime']
    del data['objects'][0]['files'][1]['utc_datetime']
    del data['instruments'][0]['instrument_log_entries'][0]['versions'][0]['utc_datetime']

    user_id = sampledb.logic.users.get_users()[0].id
    action_id = sampledb.logic.actions.get_actions(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION)[0].id
    object_id = sampledb.logic.objects.get_objects()[0].id
    instrument_id = sampledb.logic.instruments.get_instruments()[0].id
    instrument_log_entry_id = sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument_id)[0].id
    instrument_log_entry_file_id = sampledb.logic.instrument_log_entries.get_instrument_log_file_attachments(instrument_log_entry_id)[0].id
    instrument_log_category_id = sampledb.logic.instrument_log_entries.get_instrument_log_categories(instrument_id)[0].id

    expected_data = {
        'objects': [
            {
                'id': object_id,
                'action_id': action_id,
                'versions': [
                    {
                        'id': 0,
                        'user_id': user_id,
                        'schema': {
                                'type': 'object',
                                'title': 'Example Object',
                                'required': ['name'],
                                'properties': {
                                    'name': {
                                        'type': 'text',
                                        'title': 'Sample Name'
                                    }
                                }
                        },
                        'data': {
                            'name': {
                                'text': 'Object',
                                '_type': 'text'
                            }
                        }
                    }
                ],
                'comments': [],
                'location_assignments': [],
                'publications': [],
                'files': [
                    {
                        'id': 0,
                        'hidden': False,
                        'title': 'test.txt',
                        'description': None,
                        'uploader_id': user_id,
                        'original_file_name': 'test.txt',
                        'path': f'objects/{object_id}/files/0/test.txt'
                    },
                    {
                        'id': 1,
                        'hidden': False,
                        'title': 'https://example.com',
                        'description': None,
                        'uploader_id': user_id,
                        'url': 'https://example.com'
                    }
                ]
            }
        ],
        'actions': [
            {
                'id': action_id,
                'type': 'sample',
                'name': 'Example Action',
                'user_id': None,
                'instrument_id': None,
                'description': None,
                'description_is_markdown': False,
                'short_description': None,
                'short_description_is_markdown': False
            }
        ],
        'instruments': [
            {
                'id': instrument_id,
                'name': 'Example Instrument',
                'description': 'Example Instrument Description',
                'description_is_markdown': False,
                'short_description': None,
                'short_description_is_markdown': False,
                'instrument_scientist_ids': [],
                'instrument_log_entries': [
                    {
                        'id': instrument_log_entry_id,
                        'author_id': user_id,
                        'versions': [
                            {
                                'log_entry_id': instrument_log_entry_id,
                                'version_id': 1,
                                'content': 'Example Log Entry Text',
                                'categories': [
                                    {
                                        'id': instrument_log_category_id,
                                        'title': 'Category'
                                    }
                                ]
                            }
                        ],
                        'file_attachments': [
                            {
                                'file_name': 'example.txt',
                                'path': f'instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/files/{instrument_log_entry_file_id}/example.txt'
                            }
                        ],
                        'object_attachments': [
                            {
                                'object_id': object_id
                            }
                        ]
                    }
                ]
            }
        ],
        'users': [
            {
                'id': user_id,
                'name': 'Basic User',
                'orcid_id': None,
                'affiliation': None,
                'role': None
            }
        ],
        'locations': []
    }
    assert data == expected_data


def test_zip_export(user, app):
    set_up_state(user)
    object_id = sampledb.logic.objects.get_objects()[0].id
    instrument_id = sampledb.logic.instruments.get_instruments()[0].id
    instrument_log_entry_id = sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument_id)[0].id
    instrument_log_entry_file_id = sampledb.logic.instrument_log_entries.get_instrument_log_file_attachments(instrument_log_entry_id)[0].id

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        zip_bytes = export.get_zip_archive(user.id)
    app.config['SERVER_NAME'] = server_name
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
        assert zip_file.testzip() is None
        assert set(zip_file.namelist()) == {
            'sampledb_export/README.txt',
            'sampledb_export/data.json',
            f'sampledb_export/{object_id}.rdf',
            f'sampledb_export/objects/{object_id}/files/0/test.txt',
            f'sampledb_export/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/files/{instrument_log_entry_file_id}/example.txt'
        }
        with zip_file.open('sampledb_export/data.json') as data_file:
            data = json.load(data_file)
        validate_data(data)

        with zip_file.open(f'sampledb_export/objects/{object_id}/files/0/test.txt') as text_file:
            assert text_file.read().decode('utf-8') == "This is a test file."

        with zip_file.open(f'sampledb_export/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/files/{instrument_log_entry_file_id}/example.txt') as text_file:
            assert text_file.read() == b'Example Content'


def test_tar_gz_export(user, app):
    set_up_state(user)
    object_id = sampledb.logic.objects.get_objects()[0].id
    instrument_id = sampledb.logic.instruments.get_instruments()[0].id
    instrument_log_entry_id = sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument_id)[0].id
    instrument_log_entry_file_id = sampledb.logic.instrument_log_entries.get_instrument_log_file_attachments(instrument_log_entry_id)[0].id

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        zip_bytes = export.get_tar_gz_archive(user.id)
    app.config['SERVER_NAME'] = server_name
    with tarfile.open('sampledb_export.tar.gz', 'r:gz', fileobj=io.BytesIO(zip_bytes)) as tar_file:
        assert set(tar_file.getnames()) == {
            'sampledb_export/README.txt',
            'sampledb_export/data.json',
            f'sampledb_export/{object_id}.rdf',
            f'sampledb_export/objects/{object_id}/files/0/test.txt',
            f'sampledb_export/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/files/{instrument_log_entry_file_id}/example.txt'
        }
        with tar_file.extractfile('sampledb_export/data.json') as data_file:
             data = json.load(data_file)
        validate_data(data)

        with tar_file.extractfile(f'sampledb_export/objects/{object_id}/files/0/test.txt') as text_file:
            assert text_file.read().decode('utf-8') == "This is a test file."

        with tar_file.extractfile(f'sampledb_export/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/files/{instrument_log_entry_file_id}/example.txt') as text_file:
            assert text_file.read() == b'Example Content'


def test_eln_export(user, app):
    set_up_state(user)

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        zip_bytes = export.get_eln_archive(user.id)
    app.config['SERVER_NAME'] = server_name
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
        assert zip_file.testzip() is None
        with zip_file.open('sampledb_export/ro-crate-metadata.json') as data_file:
            json.load(data_file)
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_file.extractall(temp_dir)
            rocrate_dir = os.path.join(temp_dir, 'sampledb_export')
            ROCrate(rocrate_dir)
            for severity in [
                rocrate_validator.models.Severity.REQUIRED
            ]:
                result = rocrate_validator.services.validate({
                    "profiles_path": rocrate_validator.utils.get_profiles_path(),
                    "profile_identifier": "ro-crate",
                    "requirement_severity": severity.name,
                    "requirement_severity_only": False,
                    "inherit_profiles": True,
                    "verbose": True,
                    "rocrate_uri": rocrate_dir,
                    "ontology_path": None,
                    "abort_on_first": False
                })
                result_dict = result.to_dict()
                assert result_dict['issues'] == []
                assert result_dict['passed']
                assert result.passed(severity)


def test_eln_export_property_values(user, app):
    sample_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.actions.ActionType.SAMPLE_CREATION,
        schema={
            "type": "object",
            "title": {"en": "Object Information"},
            "properties": {
                "name": {
                    "type": "text",
                    "title": {"en": "Name"}
                }
            },
            "required": ["name"]
        }
    )
    referenced_object_id1 = sampledb.logic.objects.create_object(
        action_id=sample_action.id,
        data={
            "name": {
                "_type": "text",
                "text": {"en": "Referenced Object 1"},
            }
        },
        user_id=user.id
    ).id
    referenced_object_id2 = sampledb.logic.objects.create_object(
        action_id=sample_action.id,
        data={
            "name": {
                "_type": "text",
                "text": {"en": "Referenced Object 2"},
            }
        },
        user_id=user.id
    ).id
    measurement_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.actions.ActionType.MEASUREMENT,
        schema={
            "type": "object",
            "title": {"en": "Object Information"},
            "properties": {
                "name": {
                    "type": "text",
                    "title": {"en": "Name"}
                },
                "check": {
                    "type": "bool",
                    "title": {"en": "Checkbox"}
                },
                "creation_date": {
                    "type": "datetime",
                    "title": {"en": "Creation Date"}
                },
                "temperature": {
                    "type": "quantity",
                    "title": {"en": "Temperature"},
                    "units": "degC"
                },
                "samples": {
                    "type": "array",
                    "title": {"en": "Samples"},
                    "items": {
                        "type": "sample",
                        "title": {"en": "Sample"},
                    }
                },
                "operator": {
                    "type": "user",
                    "title": {"en": "Operator"}
                },
                "setup_file": {
                    "type": "file",
                    "title": {"en": "Setup File"}
                },
                "log_file": {
                    "type": "file",
                    "title": {"en": "Log File"}
                },
                "hazards": {
                    "type": "hazards",
                    "title": {"en": "GHS Hazards"}
                }
            },
            "required": ["name", "hazards"]
        }
    )
    object_id = sampledb.logic.objects.create_object(
        action_id=measurement_action.id,
        data={
            "name": {
                "_type": "text",
                "text": {"en": "Test Object"},
            },
            "check": {
                "_type": "bool",
                "value": True
            },
            "creation_date": {
                "_type": "datetime",
                "utc_datetime": "2024-01-02 03:04:05"
            },
            "temperature": {
                "_type": "quantity",
                "units": "degC",
                "magnitude": 20
            },
            "samples": [
                {
                    "_type": "sample",
                    "object_id": referenced_object_id1
                },
                {
                    "_type": "sample",
                    "object_id": referenced_object_id2
                }
            ],
            "operator": {
                "_type": "user",
                "user_id": user.id
            },
            "hazards": {
                "_type": "hazards",
                "hazards": [1, 6]
            }
        },
        user_id=user.id
    ).id
    setup_file_id = sampledb.logic.files.create_database_file(
        object_id=object_id,
        user_id=user.id,
        file_name="setup.cfg",
        save_content=lambda f: f.write(b"Setup")
    ).id
    log_file_id = sampledb.logic.files.create_database_file(
        object_id=object_id,
        user_id=user.id,
        file_name="log.txt",
        save_content=lambda f: f.write(b"Log")
    ).id
    sampledb.logic.objects.update_object(
        object_id=object_id,
        data={
            "setup_file": {
                "_type": "file",
                "file_id": setup_file_id
            },
            "log_file": {
                "_type": "file",
                "file_id": log_file_id
            },
            **sampledb.logic.objects.get_object(object_id).data
        },
        user_id=user.id
    )
    sampledb.logic.files.hide_file(
        object_id=object_id,
        file_id=log_file_id,
        user_id=user.id,
        reason='Test'
    )
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        zip_bytes = export.get_eln_archive(user.id, object_ids=[
            object_id,
            referenced_object_id1
        ])
    app.config['SERVER_NAME'] = server_name
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
        assert zip_file.testzip() is None
        with zip_file.open('sampledb_export/ro-crate-metadata.json') as data_file:
            ro_crate_metadata = json.load(data_file)
        nodes_by_id = {
            node['@id']: node
            for node in ro_crate_metadata['@graph']
        }
        assert set(nodes_by_id.keys()) == {
            'ro-crate-metadata.json',
            './',
            'SampleDB',
            './license',
            f'./objects/{object_id}/',
            f'./objects/{object_id}/properties/check',
            f'./objects/{object_id}/properties/creation_date',
            f'./objects/{object_id}/properties/hazards',
            f'./objects/{object_id}/properties/name',
            f'./objects/{object_id}/properties/operator',
            f'./objects/{object_id}/properties/samples.0',
            f'./objects/{object_id}/properties/samples.1',
            f'./objects/{object_id}/properties/temperature',
            f'./objects/{object_id}/versions/0/',
            f'./objects/{object_id}/versions/0/schema.json',
            f'./objects/{object_id}/versions/0/data.json',
            f'./objects/{object_id}/versions/0/properties/check',
            f'./objects/{object_id}/versions/0/properties/creation_date',
            f'./objects/{object_id}/versions/0/properties/hazards',
            f'./objects/{object_id}/versions/0/properties/name',
            f'./objects/{object_id}/versions/0/properties/operator',
            f'./objects/{object_id}/versions/0/properties/samples.0',
            f'./objects/{object_id}/versions/0/properties/samples.1',
            f'./objects/{object_id}/versions/0/properties/temperature',
            f'./objects/{object_id}/versions/1/',
            f'./objects/{object_id}/versions/1/schema.json',
            f'./objects/{object_id}/versions/1/data.json',
            f'./objects/{object_id}/versions/1/properties/check',
            f'./objects/{object_id}/versions/1/properties/creation_date',
            f'./objects/{object_id}/versions/1/properties/hazards',
            f'./objects/{object_id}/versions/1/properties/log_file',
            f'./objects/{object_id}/versions/1/properties/name',
            f'./objects/{object_id}/versions/1/properties/operator',
            f'./objects/{object_id}/versions/1/properties/samples.0',
            f'./objects/{object_id}/versions/1/properties/samples.1',
            f'./objects/{object_id}/versions/1/properties/setup_file',
            f'./objects/{object_id}/versions/1/properties/temperature',
            f'./objects/{object_id}/files.json',
            f'./objects/{object_id}/files/0/setup.cfg',
            f'./objects/{referenced_object_id1}/',
            f'./objects/{referenced_object_id1}/properties/name',
            f'./objects/{referenced_object_id1}/versions/0/',
            f'./objects/{referenced_object_id1}/versions/0/schema.json',
            f'./objects/{referenced_object_id1}/versions/0/data.json',
            f'./objects/{referenced_object_id1}/versions/0/properties/name',
            f'./objects/{referenced_object_id1}/files.json',
            f'./users/{user.id}'
        }
        object_node = nodes_by_id[f'./objects/{object_id}/versions/1/']
        variables_measured = [
            property_value if 'propertyID' in property_value else nodes_by_id[property_value['@id']]
            for property_value in object_node['variableMeasured']
        ]
        assert sorted(variables_measured, key=lambda p: p['propertyID']) == sorted([
            {
                "@id": f"./objects/{object_id}/versions/1/properties/name",
                "@type": "PropertyValue",
                "propertyID": "name",
                "name": "Name",
                "value": "Test Object"
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/check",
                "@type": "PropertyValue",
                "propertyID": "check",
                "name": "Checkbox",
                "value": True
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/creation_date",
                "@type": "PropertyValue",
                "name": "Creation Date",
                "propertyID": "creation_date",
                "value": "2024-01-02T03:04:05.000000",
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/temperature",
                "@type": "PropertyValue",
                "propertyID": "temperature",
                "name": "Temperature",
                "value": 20.0,
                "unitText": "degC",
                "unitCode": "CEL"
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/samples.0",
                "@type": "PropertyValue",
                "propertyID": "samples.0",
                "name": "Samples → 0",
                "value": f"./objects/{referenced_object_id1}/",
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/samples.1",
                "@type": "PropertyValue",
                "propertyID": "samples.1",
                "name": "Samples → 1",
                "value": f"http://localhost/objects/{referenced_object_id2}",
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/operator",
                "@type": "PropertyValue",
                "propertyID": "operator",
                "name": "Operator",
                "value": f"./users/{user.id}",
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/setup_file",
                "@type": "PropertyValue",
                "propertyID": "setup_file",
                "name": "Setup File",
                "value": f"./objects/{object_id}/files/{setup_file_id}/setup.cfg",
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/log_file",
                "@type": "PropertyValue",
                "propertyID": "log_file",
                "name": "Log File",
                "value": f"http://localhost/objects/{object_id}/files/{log_file_id}",
            },
            {
                "@id": f"./objects/{object_id}/versions/1/properties/hazards",
                "@type": "PropertyValue",
                "name": "GHS Hazards",
                "propertyID": "hazards",
                "value": "Explosive, Toxic"
            }
        ], key=lambda p: p['propertyID'])


def test_export_template_schema(user, app):
    template_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.TEMPLATE,
        schema={
            "type": "object",
            "title": "Template Action",
            "properties": {
                "name": {
                    "type": "text",
                    "title": "Name"
                },
                "other": {
                    "type": "text",
                    "title": "Other"
                }
            },
            "required": ["name"]
        }
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(
        action_id=template_action.id,
        permissions=sampledb.models.Permissions.READ
    )

    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema={
            "type": "object",
            "title": "Action",
            "properties": {
                "name": {
                    "type": "text",
                    "title": "Name"
                },
                "template": {
                    "type": "object",
                    "title": "Template",
                    "template": template_action.id
                }
            },
            "required": ["name"]
        }
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(
        action_id=action.id,
        permissions=sampledb.models.Permissions.READ
    )
    sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            "name": {
                "_type": "text",
                "text": "Object"
            },
            "template": {
                "other": {
                    "_type": "text",
                    "text": "Other"
                }
            }
        },
        user_id=user.id
    )

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        export_archive_files, export_infos = export.get_export_infos(user.id)
    app.config['SERVER_NAME'] = server_name

    assert export_infos['objects'][0]['versions'][0]['schema'] == {
        "type": "object",
        "title": "Action",
        "properties": {
            "name": {
                "type": "text",
                "title": "Name"
            },
            "template": {
                "type": "object",
                "title": "Template",
                "template": template_action.id,
                "properties": {
                    "other": {
                        "type": "text",
                        "title": "Other"
                    }
                },
                "required": []
            }
        },
        "required": ["name"]
    }

    action_infos_by_id = {
        action_info['id']: action_info
        for action_info in export_infos['actions']
    }
    assert set(action_infos_by_id.keys()) == {action.id, template_action.id}
