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


def test_get_action_type(flask_server, auth):
    r = requests.get(flask_server.base_url + 'api/v1/action_types/1', auth=auth)
    assert r.status_code == 404

    action_types = sampledb.logic.actions.get_action_types()

    for action_type in action_types:
        r = requests.get(flask_server.base_url + 'api/v1/action_types/{}'.format(action_type.id), auth=auth)
        assert r.status_code == 200
        assert r.json() == {
            'type_id': action_type.id,
            'name': action_type.name,
            'object_name': action_type.object_name,
            'admin_only': action_type.admin_only
        }


def test_get_action_types(flask_server, auth):
    r = requests.get(flask_server.base_url + 'api/v1/action_types/', auth=auth)
    assert r.status_code == 200
    action_types = sampledb.logic.actions.get_action_types()
    assert r.json() == [
        {
            'type_id': action_type.id,
            'name': action_type.name,
            'object_name': action_type.object_name,
            'admin_only': action_type.admin_only
        }
        for action_type in action_types
    ]
