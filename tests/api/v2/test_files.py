import base64
import hashlib
import io

import flask
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
    flask.current_app.config["SERVER_NAME"] = "localhost"
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0

    data = []
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
       "detail": "Input should be an object",
       "errors": [
           {
               "detail": "Input should be an object",
               "input": [],
               "json_pointer": "/",
           },
       ],
       "status": 400,
       "title": "Failed to validate request body data.",
       "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    data = {
        'object_id': object.id+1,
        'storage': 'database',
        'url': 'https://example.org'
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Input should be {object.object_id} (object_id)",
        "errors": [
            {
                "detail": "Input should be 1",
                "input": 2,
                "json_pointer": "/object_id",
            },
            {
                "detail": "Field required",
                "input": None,
                "json_pointer": "/original_file_name",
            },
            {
                "detail": "Field required",
                "input": None,
                "json_pointer": "/base64_content",
            },
            {
                "detail": "Extra inputs are not permitted",
                "input": "https://example.org",
                "json_pointer": "/url",
            }
        ],
       "status": 400,
       "title": "Failed to validate request body data.",
       "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    data = {
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Unable to extract tag using discriminator 'storage'",
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
        "errors": [
            {
                "detail": "Unable to extract tag using discriminator 'storage'",
                "input": {},
                "json_pointer": "/"
            }
        ]
    }

    data = {
        'storage': 'local'
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Input tag 'local' found using 'storage' does not match any of the expected tags: 'database', 'local_reference', 'url'",
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
        "errors": [
            {
               "detail": "Input tag 'local' found using 'storage' does not match any of the expected tags: 'database', 'local_reference', 'url'",
               "input": {
                   "storage": "local",
               },
               "json_pointer": "/"
            }
        ]
    }

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0


def test_create_url_file(flask_server, object, auth):
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'url',
        'url': 'https://example.org'
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 1
    assert files[0].storage == 'url'
    assert files[0].data['url'] == 'https://example.org'


def test_create_invalid_url_file(flask_server, object, auth):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0

    data = {
        'storage': 'url',
        'address': 'https://example.org'
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Field required (url)",
        "errors": [
            {
                "detail": "Field required",
                "json_pointer": "/url",
                "input": None
            },
            {
                "detail": "Extra inputs are not permitted",
                "json_pointer": "/address",
                "input": "https://example.org"
            }
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    data = {
        'storage': 'url'
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Field required (url)",
        "errors": [
            {
                "detail": "Field required",
                "json_pointer": "/url",
                "input": None
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    data = {
        'storage': 'url',
        'url': 'test.txt'
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "String should be a valid URL (url)",
        "errors": [
            {
                "detail": "String should be a valid URL",
                "json_pointer": "/url",
                "input": "test.txt"
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0


def test_create_url_file_with_files_disabled(flask_server, object, auth):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'url',
        'url': 'https://example.org'
    }
    action_type = sampledb.logic.action_types.get_action_type(sampledb.logic.action_types.ActionType.SAMPLE_CREATION)
    sampledb.logic.action_types.update_action_type(
        action_type_id=action_type.id,
        admin_only=action_type.admin_only,
        show_on_frontpage=action_type.show_on_frontpage,
        show_in_navbar=action_type.show_in_navbar,
        show_in_object_filters=action_type.show_in_object_filters,
        enable_labels=action_type.enable_labels,
        enable_files=False,
        enable_locations=action_type.enable_locations,
        enable_publications=action_type.enable_publications,
        enable_comments=action_type.enable_comments,
        enable_activity_log=action_type.enable_activity_log,
        enable_related_objects=action_type.enable_related_objects,
        enable_project_link=action_type.enable_project_link,
        enable_instrument_link=action_type.enable_instrument_link,
        disable_create_objects=action_type.disable_create_objects,
        is_template=action_type.is_template,
        usable_in_action_type_ids=[at.id for at in action_type.usable_in_action_types],
        scicat_export_type=action_type.scicat_export_type,
    )
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    assert r.json() == {
        "status": 403,
        "title": "Adding files is not enabled for this object.",
        "type": "http://localhost/api/v2/errors/ObjectFilesNotEnabled",
        "detail": f"Object #{object.object_id} was created with action #{object.action_id}, which is of action type #{action_type.id}. Adding files is not enabled for objects created with actions of that type.",
        "errors": []
    }
    assert not sampledb.logic.files.get_files_for_object(object.id)


def test_get_url_file(flask_server, object, auth, user):
    sampledb.logic.files.create_url_file(
        object_id=object.id,
        user_id=user.id,
        url='https://example.org'
    )
    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {
        'object_id': object.id,
        'file_id': 0,
        'storage': 'url',
        'url': 'https://example.org'
    }


def test_create_database_file(flask_server, object, auth):
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode('test'.encode('utf8')).decode('utf8')
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
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
        r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
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
    flask.current_app.config['SERVER_NAME'] = 'localhost'
    for i, algorithm in enumerate(['sha256', 'sha512']):
        files = sampledb.logic.files.get_files_for_object(object.id)
        assert len(files) == 0

        data = {
            'storage': 'database',
            'original_file_name': 'test.txt',
            'base64_content': base64.b64encode(f'test{i}'.encode('utf8')).decode('utf8'),
            'hash': {
                'algorithm': algorithm,
                'hexdigest': getattr(hashlib, algorithm)('test'.encode('utf8')).hexdigest()
            }
        }
        expected_hash = getattr(hashlib, algorithm)(f'test{i}'.encode('utf8')).hexdigest()
        r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
        assert r.status_code == 400
        assert r.json() == {
            "detail": f"Hash hexdigest should be {expected_hash} (hash)",
            "errors": [
                {
                    "detail": f"Hash hexdigest should be {expected_hash}",
                    "json_pointer": "/hash",
                    "input": data['hash']
                }
            ],
            "status": 400,
            "title": "Failed to validate request body data.",
            "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
        }
        files = sampledb.logic.files.get_files_for_object(object.id)
        assert len(files) == 0

    data = {
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode(f'test'.encode('utf8')).decode('utf8'),
        'hash': hashlib.sha256(f'test'.encode('utf8')).hexdigest()
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail":  "Input should be an object (hash)",
        "errors": [
            {
                "detail": "Input should be an object",
                "json_pointer": "/hash",
                "input": data['hash']
            }
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
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
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail":  "Field required (hash.algorithm)",
        "errors": [
            {
                "detail": "Field required",
                "json_pointer": "/hash/algorithm",
                "input": None
            }
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
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
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail":  "String should be exclusively lowercase hex characters (hash.hexdigest)",
        "errors": [
            {
                "detail": "String should be exclusively lowercase hex characters",
                "json_pointer": "/hash/hexdigest",
                "input": data['hash']['hexdigest']
            }
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0

    data = {
        'storage': 'database',
        'original_file_name': 'test.txt',
        'base64_content': base64.b64encode(f'test'.encode('utf8')).decode('utf8'),
        'hash': {
            'algorithm': 'md5',
            'hexdigest': hashlib.md5(f'test'.encode('utf8')).hexdigest()
        }
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail":  "Algorithm should be one of: sha256, sha512 (hash.algorithm)",
        "errors": [
            {
                "detail": "Algorithm should be one of: sha256, sha512",
                "json_pointer": "/hash/algorithm",
                "input": "md5"
            }
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
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
        r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
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
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
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
    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
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
        url='https://example.org'
    )
    sampledb.logic.files.create_database_file(
        object_id=object.id,
        user_id=user.id,
        file_name='test.txt',
        save_content=lambda stream: stream.write('test'.encode('utf8'))
    )
    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == [
        {
            'object_id': object.id,
            'file_id': 0,
            'storage': 'url',
            'url': 'https://example.org'
        },
        {
            'object_id': object.id,
            'file_id': 1,
            'storage': 'database',
            'original_file_name': 'test.txt',
            'hash': {
                'algorithm': 'sha256',
                'hexdigest': '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
            },
            'base64_content': None,
            'base64_preview_image': None,
            'preview_image_mime_type': None,
        }
    ]


def test_get_hidden_file(flask_server, object, auth, user):
    flask.current_app.config['SERVER_NAME'] = 'localhost'
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
    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 403
    assert r.json() == {
        "status": 403,
        "title": "The requested file has been hidden.",
        "type": "http://localhost/api/v2/errors/ObjectFileHidden",
        "detail": f"File #{0} of object #{object.object_id} has been hidden.",
        "errors": []
    }


def test_get_nonexistent_file(flask_server, object, auth, user):
    flask.current_app.config['SERVER_NAME'] = 'localhost'
    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/files/0'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 404
    assert r.json() == {
        "status": 404,
        "title": "The requested file does not exist.",
        "type": "http://localhost/api/v2/errors/ObjectFileNotFound",
        "detail": f"File #{0} of object #{object.object_id} does not exist.",
        "errors": []
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
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
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
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
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
    flask.current_app.config['SERVER_NAME'] = 'localhost'
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    data = {
        'storage': 'local_reference',
        'filepath': '/example/example.txt'
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    assert r.json() == {
        "status": 403,
        "title": "The user is not authorized to add this path as a local_reference file.",
        "type": "http://localhost/api/v2/errors/LocalReferencePathNotInWhitelist",
        "detail": f"User #{user.id} is not authorized to add the path '/example/example.txt' as a local_reference file. There is no matching whitelist entry.",
        "errors": []
    }
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/example/': [user.id + 1]
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    assert r.json() == {
        "status": 403,
        "title": "The user is not authorized to add this path as a local_reference file.",
        "type": "http://localhost/api/v2/errors/LocalReferencePathNotInWhitelist",
        "detail": f"User #{user.id} is not authorized to add the path '/example/example.txt' as a local_reference file. There is no matching whitelist entry.",
        "errors": []
    }
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/example1': [user.id]
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    assert r.json() == {
        "status": 403,
        "title": "The user is not authorized to add this path as a local_reference file.",
        "type": "http://localhost/api/v2/errors/LocalReferencePathNotInWhitelist",
        "detail": f"User #{user.id} is not authorized to add the path '/example/example.txt' as a local_reference file. There is no matching whitelist entry.",
        "errors": []
    }
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/': [user.id + 1]
    }
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/files/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 403
    assert r.json() == {
        "status": 403,
        "title": "The user is not authorized to add this path as a local_reference file.",
        "type": "http://localhost/api/v2/errors/LocalReferencePathNotInWhitelist",
        "detail": f"User #{user.id} is not authorized to add the path '/example/example.txt' as a local_reference file. There is no matching whitelist entry.",
        "errors": []
    }
    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 0
