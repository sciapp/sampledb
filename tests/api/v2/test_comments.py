import flask
import requests
import pytest

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


def test_create_invalid_comment(flask_server, object, auth):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    comments = sampledb.logic.comments.get_comments_for_object(object.id)
    assert len(comments) == 0

    data = []
    r = requests.post(flask_server.base_url + 'api/v2/objects/{}/comments/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
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
        'content': "Content"
    }
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Input should be {object.id} (object_id)",
        "errors": [
            {
                "detail": f"Input should be {object.id}",
                "input": object.id + 1,
                "json_pointer": "/object_id",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    data = {
    }
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Field required (content)",
        "errors": [
            {
                "detail": "Field required",
                "input": None,
                "json_pointer": "/content",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    data = {
        'content': None
    }
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Input should be a valid string (content)",
        "errors": [
            {
                "detail": "Input should be a valid string",
                "input": None,
                "json_pointer": "/content",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    data = {
        'content': ''
    }
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "String should have at least 1 character (content)",
        "errors": [
            {
                "detail": "String should have at least 1 character",
                "input": "",
                "json_pointer": "/content",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    comments = sampledb.logic.comments.get_comments_for_object(object.id)
    assert len(comments) == 0


def test_create_comment(flask_server, object, auth, user):
    comments = sampledb.logic.comments.get_comments_for_object(object.id)
    assert len(comments) == 0

    content = 'This is a test comment\n\n\ntest'
    data = {
        'content': content
    }
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    comments = sampledb.logic.comments.get_comments_for_object(object.id)
    assert len(comments) == 1
    assert comments[0].object_id == object.id
    assert comments[0].user_id == user.id
    assert comments[0].content == content


def test_get_comment(flask_server, object, auth, user):
    content = 'This is a test comment\n\n\ntest'
    comment_id = sampledb.logic.comments.create_comment(
        object_id=object.id,
        user_id=user.id,
        content=content
    )
    r = requests.get(flask_server.base_url + f'api/v2/objects/{object.id}/comments/{comment_id}', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    result_json = r.json()
    assert 'utc_datetime' in result_json
    del result_json['utc_datetime']
    assert result_json == {
        'object_id': object.id,
        'comment_id': comment_id,
        'user_id': user.id,
        'content': content
    }

    r = requests.get(flask_server.base_url + f'api/v2/objects/{object.id}/comments/{comment_id + 1}', auth=auth, allow_redirects=False)
    assert r.status_code == 404

    r = requests.get(flask_server.base_url + f'api/v2/objects/{object.id + 1}/comments/{comment_id}', auth=auth, allow_redirects=False)
    assert r.status_code == 404


def test_get_comments(flask_server, object, auth, user):
    content = 'This is a test comment\n\n\ntest'
    comment_id = sampledb.logic.comments.create_comment(
        object_id=object.id,
        user_id=user.id,
        content=content
    )
    r = requests.get(flask_server.base_url + f'api/v2/objects/{object.id}/comments/', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    result_json = r.json()
    assert len(result_json) == 1
    assert result_json == [
        {
            'object_id': object.id,
            'comment_id': comment_id,
            'user_id': user.id,
            'utc_datetime': sampledb.logic.comments.get_comment(comment_id).utc_datetime.isoformat().replace('+00:00', 'Z'),
            'content': content
        }
    ]
