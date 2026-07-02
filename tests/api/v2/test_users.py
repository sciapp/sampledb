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
    r = requests.get(flask_server.base_url + 'api/v1/users/10', auth=auth)
    assert r.status_code == 404

    r = requests.get(flask_server.base_url + 'api/v1/users/{}'.format(user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'user_id': user.id,
        'name': "Basic User",
        'orcid': None,
        'affiliation': None,
        'role': None
    }

    sampledb.logic.users.set_user_administrator(user.id, True)

    r = requests.get(flask_server.base_url + 'api/v1/users/{}'.format(user.id), auth=auth)
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
    r = requests.get(flask_server.base_url + 'api/v1/users/me', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'user_id': user.id,
        'name': "Basic User",
        'orcid': None,
        'affiliation': None,
        'role': None
    }


def test_get_users(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/users/', auth=auth)
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
        r = requests.get(flask_server.base_url + 'api/v1/users/', auth=auth, params={param: str(value).lower()})
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
