# coding: utf-8
"""

"""
import base64
from urllib.parse import urlencode

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
def users(user):
    return [user] + [
        sampledb.logic.users.create_user(name=f"User {i}", email="example@example.com", type=sampledb.models.UserType.PERSON)
        for i in range(3)
    ]


def test_get_user(flask_server, auth, user):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + f'api/v2/users/{user.id + 1}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": f"User #{user.id + 1} does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested user does not exist.",
        "type": "http://localhost/api/v2/errors/UserNotFound",
    }

    r = requests.get(flask_server.base_url + 'api/v2/users/{}'.format(user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'user_id': user.id,
        'name': "Basic User",
        'orcid': None,
        'affiliation': None,
        'role': None,
        'email': None,
        'is_active': None,
        'is_hidden': None,
        'is_readonly': None,
    }

    sampledb.logic.users.set_user_administrator(user.id, True)

    r = requests.get(flask_server.base_url + 'api/v2/users/{}'.format(user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'user_id': user.id,
        'name': "Basic User",
        'orcid': None,
        'affiliation': None,
        'role': None,
        'email': user.email,
        'is_hidden': user.is_hidden,
        'is_active': user.is_active,
        'is_readonly': user.is_readonly,
    }


def test_get_current_user(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v2/users/me', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'user_id': user.id,
        'name': "Basic User",
        'orcid': None,
        'affiliation': None,
        'role': None,
        'email': None,
        'is_active': None,
        'is_hidden': None,
        'is_readonly': None,
    }


def test_get_users(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v2/users/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'user_id': user.id,
            'name': "Basic User",
            'orcid': None,
            'affiliation': None,
            'role': None
        }
    ]

@pytest.mark.parametrize(
    ['param', 'getter', 'setter'],
    [
        ('filter_hidden', lambda user: user.is_hidden, lambda user, value: sampledb.logic.users.set_user_hidden(user.id, value)),
        ('filter_active', lambda user: user.is_active, lambda user, value: sampledb.logic.users.set_user_active(user.id, value)),
        ('filter_readonly', lambda user: user.is_readonly, lambda user, value: sampledb.logic.users.set_user_readonly(user.id, value)),
    ]
)
def test_get_users(flask_server, auth, user, users, param, getter, setter):
    sampledb.logic.users.set_user_administrator(user.id, True)
    setter(users[-1], True)
    setter(users[-2], False)
    # reload users after making these changes
    users = [
        sampledb.logic.users.get_user(user.id)
        for user in users
    ]
    for value in [True, False]:
        r = requests.get(flask_server.base_url + 'api/v2/users/', auth=auth, params={param: str(value).lower()})
        assert r.status_code == 200
        assert r.json() == [
            {
                'user_id': user.id,
                'name': user.name,
                'orcid': None,
                'affiliation': None,
                'role': None,
                'email': user.email,
                'is_hidden': user.is_hidden,
                'is_active': user.is_active,
                'is_readonly': user.is_readonly,
            }
            for user in users
            if getter(user) == value
        ]

def test_get_users_pagination(flask_server, auth, user):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + 'api/v2/users/?&limit=10', auth=auth)
    assert r.status_code == 200
    assert len(r.json()) == 1

    users = [user] + [
        sampledb.logic.users.create_user(
            name=f"User {i}",
            email=f"user{i}@example.com",
            type=sampledb.models.UserType.PERSON,
            affiliation=None,
            role=None,
        )
        for i in range(30)
    ]

    r = requests.get(flask_server.base_url + 'api/v2/users/?limit=10', auth=auth)
    assert r.status_code == 200
    assert [
        user["name"]
        for user in r.json()
    ] == [
        user.name
        for user in users[:10]
    ]
    assert r.headers['Link'] == ', '.join(
        [
            '<http://localhost/api/v2/users/?limit=10>; rel="start"',
            '<http://localhost/api/v2/users/?limit=10>; rel="self"',
            f'<http://localhost/api/v2/users/?' + urlencode({"limit": 10, "cursor": base64.urlsafe_b64encode(str(users[9].id).encode('utf8')).decode('utf8')}) + '>; rel="next"',
        ]
    )
    r = requests.get(flask_server.base_url + 'api/v2/users/?' + urlencode({"limit": 5, "cursor": base64.urlsafe_b64encode(str(users[9].id).encode('utf8')).decode('utf8')}), auth=auth)
    assert r.status_code == 200
    assert [
        user["name"]
        for user in r.json()
    ] == [
        user.name
        for user in users[10:15]
    ]
    assert r.headers['Link'] == ', '.join(
        [
            '<http://localhost/api/v2/users/?limit=5>; rel="start"',
            f'<http://localhost/api/v2/users/?' + urlencode({"limit": 5, "cursor": base64.urlsafe_b64encode(str(users[9].id).encode('utf8')).decode('utf8')}) + '>; rel="self"',
            f'<http://localhost/api/v2/users/?' + urlencode({"limit": 5, "cursor": base64.urlsafe_b64encode(str(users[14].id).encode('utf8')).decode('utf8')}) + '>; rel="next"',
        ]
    )
