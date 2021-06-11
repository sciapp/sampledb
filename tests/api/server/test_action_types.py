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


def test_get_action_type(flask_server, auth):
    r = requests.get(flask_server.base_url + 'api/v1/action_types/1', auth=auth)
    assert r.status_code == 404

    action_types = sampledb.logic.actions.get_action_types()

    for action_type in action_types:
        action_type_translation = sampledb.logic.action_type_translations.get_action_type_translation_for_action_type_in_language(
            action_type.id,
            language_id=sampledb.logic.languages.Language.ENGLISH
        )
        r = requests.get(flask_server.base_url + 'api/v1/action_types/{}'.format(action_type.id), auth=auth)
        assert r.status_code == 200
        assert r.json() == {
            'type_id': action_type.id,
            'name': action_type_translation.name,
            'object_name': action_type_translation.object_name,
            'admin_only': action_type.admin_only
        }


def test_get_action_types(flask_server, auth):
    r = requests.get(flask_server.base_url + 'api/v1/action_types/', auth=auth)
    assert r.status_code == 200
    expected_json = []
    for action_type in sampledb.logic.actions.get_action_types():
        action_type_translation = sampledb.logic.action_type_translations.get_action_type_translation_for_action_type_in_language(
            action_type.id,
            language_id=sampledb.logic.languages.Language.ENGLISH
        )
        expected_json.append({
            'type_id': action_type.id,
            'name': action_type_translation.name,
            'object_name': action_type_translation.object_name,
            'admin_only': action_type.admin_only
        })
    assert r.json() == expected_json
