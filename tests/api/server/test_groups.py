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


def test_get_group(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/group/10', auth=auth)
    assert r.status_code == 404

    group = sampledb.logic.groups.create_group(name='Test Group', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v1/groups/{group.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'group_id': group.id,
        'name': {"en": "Test Group"},
        'description': {},
        "member_users": [
            {
                "user_id": user.id,
                "href": flask_server.base_url + f'api/v1/users/{user.id}',
            }
        ]
    }


def test_get_groups(flask_server, auth, user):
    r = requests.get(flask_server.base_url + f'api/v1/groups/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    group = sampledb.logic.groups.create_group(name='Test Group', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v1/groups/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'group_id': group.id,
            'name': {"en": "Test Group"},
            'description': {},
            "member_users": [
                {
                    "user_id": user.id,
                    "href": flask_server.base_url + f'api/v1/users/{user.id}',
                }
            ]
        }
    ]
