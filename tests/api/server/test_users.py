# coding: utf-8
"""

"""

import requests
import pytest
import json

import sampledb
import sampledb.logic
import sampledb.models


from tests.test_utils import flask_server, app, app_context


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
def action():
    action = sampledb.logic.actions.create_action(
        action_type=sampledb.logic.actions.ActionType.SAMPLE_CREATION,
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
    return action


def test_get_user(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/users/10', auth=auth)
    assert r.status_code == 404

    r = requests.get(flask_server.base_url + 'api/v1/users/{}'.format(user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'user_id': user.id,
        'name': "Basic User"
    }


def test_get_current_user(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/users/me', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'user_id': user.id,
        'name': "Basic User"
    }


def test_get_users(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/users/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'user_id': user.id,
            'name': "Basic User"
        }
    ]
