# coding: utf-8
"""

"""

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


def test_create_invalid_comment(flask_server, object, auth):
    comments = sampledb.logic.comments.get_comments_for_object(object.id)
    assert len(comments) == 0

    data = []
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/comments/'.format(object.object_id), json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON object body required"
    }

    data = {
        'object_id': object.id+1,
        'content': "Content"
    }
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": f"object_id must be {object.id}"
    }

    data = {
    }
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "content must be set"
    }

    data = {
        'content': None
    }
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "content must be a string"
    }

    data = {
        'content': ''
    }
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json() == {
        "message": "content must not be empty"
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
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/comments/', json=data, auth=auth, allow_redirects=False)
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
    r = requests.get(flask_server.base_url + f'api/v1/objects/{object.id}/comments/{comment_id}', auth=auth, allow_redirects=False)
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

    r = requests.get(flask_server.base_url + f'api/v1/objects/{object.id}/comments/{comment_id + 1}', auth=auth, allow_redirects=False)
    assert r.status_code == 404

    r = requests.get(flask_server.base_url + f'api/v1/objects/{object.id + 1}/comments/{comment_id}', auth=auth, allow_redirects=False)
    assert r.status_code == 404


def test_get_comments(flask_server, object, auth, user):
    content = 'This is a test comment\n\n\ntest'
    comment_id = sampledb.logic.comments.create_comment(
        object_id=object.id,
        user_id=user.id,
        content=content
    )
    r = requests.get(flask_server.base_url + f'api/v1/objects/{object.id}/comments/', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    result_json = r.json()
    assert len(result_json) == 1
    assert 'utc_datetime' in result_json[0]
    del result_json[0]['utc_datetime']
    assert result_json == [
        {
            'object_id': object.id,
            'comment_id': comment_id,
            'user_id': user.id,
            'content': content
        }
    ]

