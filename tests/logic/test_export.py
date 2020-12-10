# coding: utf-8
"""

"""

import io
import json
import tarfile
import zipfile

import pytest

import sampledb
from sampledb.models import User
from sampledb.logic import export, objects, actions, files


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def set_up_state(user: User):
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
    actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Irrelevant Action',
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
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    object = objects.create_object(user_id=user.id, action_id=action.id, data=data)
    def save_content(file): file.write("This is a test file.".encode('utf-8'))
    files.create_local_file(object.id, user.id, "test.txt", save_content)
    files.create_url_file(object.id, user.id, "https://example.com")

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="Example Instrument Description",
        users_can_view_log_entries=True
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
    action_id = sampledb.logic.actions.get_actions(sampledb.models.ActionType.SAMPLE_CREATION)[0].id
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
                'description': '',
                'description_is_markdown': False,
                'short_description': '',
                'short_description_is_markdown': False
            }
        ],
        'instruments': [
            {
                'id': instrument_id,
                'name': 'Example Instrument',
                'description': 'Example Instrument Description',
                'description_is_markdown': False,
                'short_description': '',
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
                'affiliation': None
            }
        ],
        'locations': []
    }
    assert data == expected_data


def test_zip_export(user, app, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

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


def test_tar_gz_export(user, app, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

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
