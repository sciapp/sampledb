# coding: utf-8
"""

"""

import requests
import pytest
import secrets

import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def auth_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        api_token = secrets.token_hex(32)
        sampledb.logic.authentication.add_api_token(user.id, api_token, 'Demo API Token')
    return {'Authorization': 'Bearer ' + api_token}, user


@pytest.fixture
def action():
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
    return action


def test_api_log_per_request(flask_server, auth_user, action):
    auth, user = auth_user
    api_token_id = sampledb.models.authentication.Authentication.query.all()[0].id

    requests.get(flask_server.base_url + 'api/v1/objects/1/versions/0', headers=auth)
    api_log_entries = sampledb.logic.api_log.get_api_log_entries(api_token_id=api_token_id)
    assert len(api_log_entries) == 1
    assert api_log_entries[0].route == '/api/v1/objects/1/versions/0'
    assert api_log_entries[0].method == sampledb.logic.api_log.HTTPMethod.GET

    requests.post(flask_server.base_url + 'api/v1/objects/1/versions/', headers=auth)
    api_log_entries = sampledb.logic.api_log.get_api_log_entries(api_token_id=api_token_id)
    assert len(api_log_entries) == 2
    assert api_log_entries[0].route == '/api/v1/objects/1/versions/'
    assert api_log_entries[0].method == sampledb.logic.api_log.HTTPMethod.POST
    assert api_log_entries[1].route == '/api/v1/objects/1/versions/0'
    assert api_log_entries[1].method == sampledb.logic.api_log.HTTPMethod.GET


def test_api_log_remove_token(flask_server, auth_user, action):
    auth, user = auth_user
    api_token_id = sampledb.models.authentication.Authentication.query.all()[0].id

    requests.get(flask_server.base_url + 'api/v1/objects/1/versions/0', headers=auth)
    api_log_entries = sampledb.logic.api_log.get_api_log_entries(api_token_id=api_token_id)
    assert len(api_log_entries) == 1
    assert api_log_entries[0].route == '/api/v1/objects/1/versions/0'
    assert api_log_entries[0].method == sampledb.logic.api_log.HTTPMethod.GET

    sampledb.logic.authentication.remove_authentication_method(api_token_id)

    api_log_entries = sampledb.logic.api_log.get_api_log_entries(api_token_id=api_token_id)
    assert len(api_log_entries) == 0
