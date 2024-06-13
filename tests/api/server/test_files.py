# coding: utf-8
"""

"""

import base64
import hashlib
import io

import requests
import pytest
from PIL import Image

import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def auth_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
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


def test_create_invalid_file(flask_server, object, auth):
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
        'storage': 'database',
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
        'storage': 'local'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "storage must be 'local_reference', 'database' or 'url'"
    }

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0


def test_create_url_file(flask_server, object, auth):
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


def test_create_invalid_url_file(flask_server, object, auth):
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


def test_get_url_file(flask_server, object, auth, user):
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


def test_create_database_file(flask_server, object, auth):
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode('test'.encode('utf8')).decode('utf8')
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 1
    assert files[0].storage == 'database'
    assert files[0].original_file_name == 'test.txt'
    with files[0].open() as f:
        assert f.read().decode('utf-8') == 'test'
    assert files[0].hash is not None
    assert files[0].hash.algorithm == sampledb.logic.files.DEFAULT_HASH_ALGORITHM
    assert files[0].hash.hexdigest == getattr(hashlib, sampledb.logic.files.DEFAULT_HASH_ALGORITHM)(f'test'.encode('utf8')).hexdigest()


def test_create_database_file_with_hash(flask_server, object, auth):
    for i, algorithm in enumerate(['sha256', 'sha512']):
        files = sampledb.logic.files.get_files_for_object(object.id)
        assert len(files) == i

        data = {
            'storage': 'database',
            'original_file_name': 'test.txt',
            'base64_content': base64.b64encode(f'test{i}'.encode('utf8')).decode('utf8'),
            'hash': {
                'algorithm': algorithm,
                'hexdigest': getattr(hashlib, algorithm)(f'test{i}'.encode('utf8')).hexdigest()
            }
        }
        r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
        assert r.status_code == 201
        files = sampledb.logic.files.get_files_for_object(object.id)
        assert len(files) == i + 1
        assert files[i].storage == 'database'
        assert files[i].original_file_name == 'test.txt'
        with files[i].open() as f:
            assert f.read().decode('utf-8') == f'test{i}'
        assert files[i].hash is not None
        assert files[i].hash.algorithm == algorithm
        assert files[i].hash.hexdigest == data['hash']['hexdigest']


def test_create_database_file_with_invalid_hash(flask_server, object, auth):
    for i, algorithm in enumerate(['sha256', 'sha512']):
        files = sampledb.logic.files.get_files_for_object(object.id)
        assert len(files) == 0

        data = {
            'storage': 'database',
            'original_file_name': 'test.txt',
            'base64_content': base64.b64encode(f'test{i}'.encode('utf8')).decode('utf8'),
            'hash': {
                'algorithm': algorithm,
                'hexdigest': getattr(hashlib, algorithm)(f'test'.encode('utf8')).hexdigest()
            }
        }
        r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
        assert r.status_code == 400
        files = sampledb.logic.files.get_files_for_object(object.id)
        assert len(files) == 0

    data = {
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode(f'test'.encode('utf8')).decode('utf8'),
        'hash': hashlib.sha256(f'test'.encode('utf8')).hexdigest()
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0

    data = {
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode(f'test'.encode('utf8')).decode('utf8'),
        'hash': {
            'hexdigest': hashlib.sha256(f'test'.encode('utf8')).hexdigest()
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0

    data = {
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode(f'test'.encode('utf8')).decode('utf8'),
        'hash': {
            'algorithm': 'sha256',
            'hexdigest': hashlib.sha256(f'test'.encode('utf8')).hexdigest().upper()
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0


def test_create_database_file_with_invalid_hash_algorithms(flask_server, object, auth):
    for i, algorithm in enumerate(['md5', 'sha1']):
        files = sampledb.logic.files.get_files_for_object(object.id)
        assert len(files) == 0

        data = {
            'storage': 'database',
            'original_file_name': 'test.txt',
            'base64_content': base64.b64encode(f'test{i}'.encode('utf8')).decode('utf8'),
            'hash': {
                'algorithm': algorithm,
                'hexdigest': getattr(hashlib, algorithm)(f'test{i}'.encode('utf8')).hexdigest()
            }
        }
        r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
        assert r.status_code == 400
        files = sampledb.logic.files.get_files_for_object(object.id)
        assert len(files) == 0


def test_create_database_file_with_preview_image(flask_server, object, auth):
    preview_image = Image.new('RGBA', (100, 100), (255, 255, 255, 255))
    preview_image_stream = io.BytesIO()
    preview_image.save(preview_image_stream, format='PNG')
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode('test'.encode('utf8')).decode('utf8'),
        'preview_image_mime_type': 'image/png',
        'base64_preview_image': base64.b64encode(preview_image_stream.getvalue()).decode('utf8')
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 1
    assert files[0].storage == 'database'
    assert files[0].original_file_name == 'test.txt'
    with files[0].open() as f:
        assert f.read().decode('utf-8') == 'test'
    assert files[0].hash is not None
    assert files[0].hash.algorithm == sampledb.logic.files.DEFAULT_HASH_ALGORITHM
    assert files[0].hash.hexdigest == getattr(hashlib, sampledb.logic.files.DEFAULT_HASH_ALGORITHM)(f'test'.encode('utf8')).hexdigest()
    assert files[0].preview_image_mime_type == 'image/png'
    assert files[0].preview_image_binary_data == preview_image_stream.getvalue()


def test_get_database_file(flask_server, object, auth, user, tmpdir):
    preview_image = Image.new('RGBA', (100, 100), (255, 255, 255, 255))
    preview_image_stream = io.BytesIO()
    preview_image.save(preview_image_stream, format='PNG')
    sampledb.logic.files.create_database_file(
        object_id=object.id,
        user_id=user.id,
        file_name='test.txt',
        save_content=lambda stream: stream.write('test'.encode('utf8')),
        preview_image_mime_type='image/png',
        preview_image_binary_data=preview_image_stream.getvalue()
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {
        'object_id': object.id,
        'file_id': 0,
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode('test'.encode('utf8')).decode('utf8'),
        'hash': {
            'algorithm': sampledb.logic.files.DEFAULT_HASH_ALGORITHM,
            'hexdigest': sampledb.logic.files.File.HashInfo.from_binary_data(
                algorithm=sampledb.logic.files.DEFAULT_HASH_ALGORITHM,
                binary_data=b'test'
            ).hexdigest
        },
        'preview_image_mime_type': 'image/png',
        'base64_preview_image': base64.b64encode(preview_image_stream.getvalue()).decode('utf8')
    }


def test_get_files(flask_server, object, auth, user):
    sampledb.logic.files.create_url_file(
        object_id=object.id,
        user_id=user.id,
        url='https://iffsamples.fz-juelich.de'
    )
    sampledb.logic.files.create_database_file(
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
            'storage': 'database',
            'original_file_name': 'test.txt',
            'hash': {
                'algorithm': 'sha256',
                'hexdigest': '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
            }
        }
    ]


def test_get_hidden_file(flask_server, object, auth, user):
    sampledb.logic.files.create_database_file(
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


def test_get_nonexistent_file(flask_server, object, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 404
    assert r.json() == {
        "message": "file {} of object {} does not exist".format(0, object.object_id)
    }


def test_create_local_reference_file(flask_server, object, auth, user):
    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/example/': [user.id]
    }
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'local_reference',
        'filepath': '/example/example.txt',
        'hash': {
            'algorithm': 'sha256',
            'hexdigest': hashlib.sha256(b'test').hexdigest()
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 1
    assert files[0].storage == 'local_reference'
    assert files[0].filepath == '/example/example.txt'
    assert files[0].hash == sampledb.logic.files.File.HashInfo(
        algorithm='sha256',
        hexdigest=hashlib.sha256(b'test').hexdigest()
    )
    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/': [user.id]
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 2
    assert files[1].storage == 'local_reference'
    assert files[1].filepath == '/example/example.txt'
    assert files[1].hash == sampledb.logic.files.File.HashInfo(
        algorithm='sha256',
        hexdigest=hashlib.sha256(b'test').hexdigest()
    )


def test_create_local_reference_file_without_permissions(flask_server, object, auth, user):
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'local_reference',
        'filepath': '/example/example.txt'
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/example/': [user.id + 1]
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/example1': [user.id]
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/': [user.id + 1]
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
