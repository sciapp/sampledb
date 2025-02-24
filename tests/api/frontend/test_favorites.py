import requests
import pytest

import sampledb
import sampledb.logic


@pytest.fixture
def user(flask_server):
    return sampledb.logic.users.create_user(
        name="Basic User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )


@pytest.fixture
def instrument():
    instrument = sampledb.logic.instruments.create_instrument()
    sampledb.logic.instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Instrument",
        description="This is an example instrument",
    )
    return instrument


@pytest.fixture
def action():
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
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    return action


def test_add_favorite_action(flask_server, user, action):
    session = requests.session()
    assert session.get(flask_server.base_url + f'users/{user.id}/autologin').status_code == 200

    assert action.id not in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)
    assert session.put(flask_server.base_url + f'api/frontend/favorite_actions/{action.id}').status_code == 200
    assert action.id in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)

    assert session.put(flask_server.base_url + f'api/frontend/favorite_actions/{action.id}').status_code == 409
    assert action.id in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)

    assert session.put(flask_server.base_url + f'api/frontend/favorite_actions/{action.id+1}').status_code == 404

    sampledb.logic.users.set_user_readonly(user.id, True)
    sampledb.logic.favorites.remove_favorite_action(action_id=action.id, user_id=user.id)
    assert action.id not in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)
    assert session.put(flask_server.base_url + f'api/frontend/favorite_actions/{action.id}').status_code == 403
    assert action.id not in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)

def test_remove_favorite_action(flask_server, user, action):
    session = requests.session()
    assert session.get(flask_server.base_url + f'users/{user.id}/autologin').status_code == 200
    sampledb.logic.favorites.add_favorite_action(action_id=action.id, user_id=user.id)

    assert action.id in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)
    assert session.delete(flask_server.base_url + f'api/frontend/favorite_actions/{action.id}').status_code == 200
    assert action.id not in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)

    assert session.delete(flask_server.base_url + f'api/frontend/favorite_actions/{action.id}').status_code == 404
    assert action.id not in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)

    assert session.delete(flask_server.base_url + f'api/frontend/favorite_actions/{action.id+1}').status_code == 404

    sampledb.logic.users.set_user_readonly(user.id, True)
    sampledb.logic.favorites.add_favorite_action(action_id=action.id, user_id=user.id)
    assert action.id in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)
    assert session.delete(flask_server.base_url + f'api/frontend/favorite_actions/{action.id}').status_code == 403
    assert action.id in sampledb.logic.favorites.get_user_favorite_action_ids(user.id)

def test_add_favorite_instrument(flask_server, user, instrument):
    session = requests.session()
    assert session.get(flask_server.base_url + f'users/{user.id}/autologin').status_code == 200

    assert instrument.id not in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)
    assert session.put(flask_server.base_url + f'api/frontend/favorite_instruments/{instrument.id}').status_code == 200
    assert instrument.id in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)

    assert session.put(flask_server.base_url + f'api/frontend/favorite_instruments/{instrument.id}').status_code == 409
    assert instrument.id in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)

    assert session.put(flask_server.base_url + f'api/frontend/favorite_instruments/{instrument.id+1}').status_code == 404

    sampledb.logic.users.set_user_readonly(user.id, True)
    sampledb.logic.favorites.remove_favorite_instrument(instrument_id=instrument.id, user_id=user.id)
    assert instrument.id not in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)
    assert session.put(flask_server.base_url + f'api/frontend/favorite_instruments/{instrument.id}').status_code == 403
    assert instrument.id not in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)


def test_remove_favorite_instrument(flask_server, user, instrument):
    session = requests.session()
    assert session.get(flask_server.base_url + f'users/{user.id}/autologin').status_code == 200
    sampledb.logic.favorites.add_favorite_instrument(instrument_id=instrument.id, user_id=user.id)

    assert instrument.id in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)
    assert session.delete(flask_server.base_url + f'api/frontend/favorite_instruments/{instrument.id}').status_code == 200
    assert instrument.id not in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)

    assert session.delete(flask_server.base_url + f'api/frontend/favorite_instruments/{instrument.id}').status_code == 404
    assert instrument.id not in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)

    assert session.delete(flask_server.base_url + f'api/frontend/favorite_instruments/{instrument.id+1}').status_code == 404

    sampledb.logic.users.set_user_readonly(user.id, True)
    sampledb.logic.favorites.add_favorite_instrument(instrument_id=instrument.id, user_id=user.id)
    assert instrument.id in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)
    assert session.delete(flask_server.base_url + f'api/frontend/favorite_instruments/{instrument.id}').status_code == 403
    assert instrument.id in sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id)
