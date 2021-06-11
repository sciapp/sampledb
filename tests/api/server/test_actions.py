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


def test_get_action(flask_server, auth):
    r = requests.get(flask_server.base_url + 'api/v1/actions/1', auth=auth)
    assert r.status_code == 404

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
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name="Example Action",
        description="This is an example action",
    )
    sampledb.logic.action_permissions.set_action_public(action.id)
    r = requests.get(flask_server.base_url + 'api/v1/actions/{}'.format(action.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'action_id': action.id,
        'instrument_id': None,
        'user_id': None,
        'type': 'sample',
        'type_id': sampledb.models.ActionType.SAMPLE_CREATION,
        'name': "Example Action",
        'description': "This is an example action",
        'is_hidden': False,
        'schema': {
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
    }


def test_get_actions(flask_server, auth, auth_user):
    r = requests.get(flask_server.base_url + 'api/v1/actions/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        user_id=auth_user[1].id,
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
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name="Example Action",
        description="This is an example action",
    )
    sampledb.logic.action_permissions.set_action_public(action.id)
    r = requests.get(flask_server.base_url + 'api/v1/actions/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'action_id': action.id,
            'instrument_id': None,
            'user_id': auth_user[1].id,
            'type': 'sample',
            'type_id': sampledb.models.ActionType.SAMPLE_CREATION,
            'name': "Example Action",
            'description': "This is an example action",
            'is_hidden': False,
            'schema': {
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
        }
    ]
