# coding: utf-8
"""

"""

import io
import json
import tarfile
import zipfile

import pytest

import sampledb
from sampledb.models import User, ActionType
from sampledb.logic import export, objects, actions, files

from ..test_utils import app_context, app, flask_server


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
        action_type=ActionType.SAMPLE_CREATION,
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
        action_type=ActionType.SAMPLE_CREATION,
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


def validate_data(data):
    # remove datetimes before comparison
    del data['objects'][0]['versions'][0]['utc_datetime']
    del data['objects'][0]['files'][0]['utc_datetime']
    del data['objects'][0]['files'][1]['utc_datetime']

    assert data == {
        'objects': [
            {
                'id': 1,
                'action_id': 1,
                'versions': [
                    {
                        'id': 0,
                        'user_id': 1,
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
                        'uploader_id': 1,
                        'original_file_name': 'test.txt',
                        'path': 'objects/1/files/0/test.txt'
                    },
                    {
                        'id': 1,
                        'hidden': False,
                        'title': 'https://example.com',
                        'description': None,
                        'uploader_id': 1,
                        'url': 'https://example.com'
                    }
                ]
            }
        ],
        'actions': [
            {
                'id': 1,
                'type': 'sample_creation',
                'name': 'Example Action',
                'user_id': None,
                'instrument_id': None,
                'description': '',
                'description_as_html': None
            }
        ],
        'instruments': [],
        'users': [
            {
                'id': 1,
                'name': 'Basic User'
            }
        ],
        'locations': []
    }


def test_zip_export(user, app, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    set_up_state(user)

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
            'sampledb_export/objects/1/files/0/test.txt'
        }
        with zip_file.open('sampledb_export/data.json') as data_file:
            data = json.load(data_file)
        validate_data(data)

        with zip_file.open('sampledb_export/objects/1/files/0/test.txt') as text_file:
            assert text_file.read().decode('utf-8') == "This is a test file."


def test_tar_gz_export(user, app, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    set_up_state(user)

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        zip_bytes = export.get_tar_gz_archive(user.id)
    app.config['SERVER_NAME'] = server_name
    with tarfile.open('sampledb_export.tar.gz', 'r:gz', fileobj=io.BytesIO(zip_bytes)) as tar_file:
        assert set(tar_file.getnames()) == {
            'sampledb_export/README.txt',
            'sampledb_export/data.json',
            'sampledb_export/objects/1/files/0/test.txt'
        }
        with tar_file.extractfile('sampledb_export/data.json') as data_file:
             data = json.load(data_file)
        validate_data(data)

        with tar_file.extractfile('sampledb_export/objects/1/files/0/test.txt') as text_file:
            assert text_file.read().decode('utf-8') == "This is a test file."
