# coding: utf-8
"""

"""

import base64
import requests
import pytest

import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def auth_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
        assert user.id is not None
    return ('username', 'password'), user


@pytest.fixture
def auth(auth_user):
    return auth_user[0]


@pytest.fixture
def user(auth_user):
    return auth_user[1]


@pytest.fixture
def object(user):
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name="",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data = {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        },
        user_id=user.id
    )
    return object


def test_create_invalid_file(flask_server, object, auth, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0

    data = []
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON object body required".format(0, object.object_id)
    }

    data = {
        'object_id': object.id+1,
        'storage': 'local',
        'url': 'https://iffsamples.fz-juelich.de'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "object_id must be {}".format(object.object_id)
    }

    data = {
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "storage must be set"
    }

    data = {
        'storage': 'invalid'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "storage must be 'local' or 'url'"
    }

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0


def test_create_local_file(flask_server, object, auth, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'local',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode('test'.encode('utf8')).decode('utf8')
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 1
    assert files[0].storage == 'local'
    assert files[0].original_file_name == 'test.txt'
    with files[0].open() as f:
        assert f.read().decode('utf-8') == 'test'


def test_create_invalid_local_file(flask_server, object, auth, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0

    data = {
        'storage': 'local',
        'file_name': 'test.txt'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "invalid key 'file_name'"
    }

    data = {
        'storage': 'local'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "original_file_name must be set for files with local storage"
    }

    data = {
        'storage': 'local',
        'original_file_name': 'test.txt'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "base64_content must be set for files with local storage"
    }

    data = {
        'storage': 'local',
        'original_file_name': 'test.txt',
        'base64_content': "test!"
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "base64_content must be base64 encoded"
    }

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0


def test_create_url_file(flask_server, object, auth, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'url',
        'url': 'https://iffsamples.fz-juelich.de'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 1
    assert files[0].storage == 'url'
    assert files[0].data['url'] == 'https://iffsamples.fz-juelich.de'


def test_create_invalid_url_file(flask_server, object, auth, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0

    data = {
        'storage': 'url',
        'address': 'https://iffsamples.fz-juelich.de'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "invalid key 'address'"
    }

    data = {
        'storage': 'url'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "url must be set for files with url storage"
    }

    data = {
        'storage': 'url',
        'url': 'test.txt'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "url must be a valid url"
    }

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0


def test_get_url_file(flask_server, object, auth, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    sampledb.logic.files.create_url_file(
        object_id=object.id,
        user_id=user.id,
        url='https://iffsamples.fz-juelich.de'
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {
        'object_id': object.id,
        'file_id': 0,
        'storage': 'url',
        'url': 'https://iffsamples.fz-juelich.de'
    }


def test_get_local_file(flask_server, object, auth, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    sampledb.logic.files.create_local_file(
        object_id=object.id,
        user_id=user.id,
        file_name='test.txt',
        save_content=lambda stream: stream.write('test'.encode('utf8'))
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {
        'object_id': object.id,
        'file_id': 0,
        'storage': 'local',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode('test'.encode('utf8')).decode('utf8')
    }


def test_get_files(flask_server, object, auth, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    sampledb.logic.files.create_url_file(
        object_id=object.id,
        user_id=user.id,
        url='https://iffsamples.fz-juelich.de'
    )
    sampledb.logic.files.create_local_file(
        object_id=object.id,
        user_id=user.id,
        file_name='test.txt',
        save_content=lambda stream: stream.write('test'.encode('utf8'))
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == [
        {
            'object_id': object.id,
            'file_id': 0,
            'storage': 'url',
            'url': 'https://iffsamples.fz-juelich.de'
        },
        {
            'object_id': object.id,
            'file_id': 1,
            'storage': 'local',
            'original_file_name': 'test.txt'
        }
    ]


def test_get_hidden_file(flask_server, object, auth, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    sampledb.logic.files.create_local_file(
        object_id=object.id,
        user_id=user.id,
        file_name='test.txt',
        save_content=lambda stream: stream.write('test'.encode('utf8'))
    )
    sampledb.logic.files.hide_file(
        object_id=object.id,
        file_id=0,
        user_id=user.id,
        reason=''
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 403
    assert r.json() == {
        "message": "file {} of object {} has been hidden".format(0, object.object_id)
    }


def test_get_nonexistent_file(flask_server, object, auth, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 404
    assert r.json() == {
        "message": "file {} of object {} does not exist".format(0, object.object_id)
    }
