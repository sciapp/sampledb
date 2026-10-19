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


def test_get_action(flask_server, auth):
    r = requests.get(flask_server.base_url + 'api/v2/actions/1', auth=auth)
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
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v2/actions/{}'.format(action.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'action_id': action.id,
        'instrument_id': None,
        'user_id': None,
        'type': 'sample',
        'type_id': sampledb.models.ActionType.SAMPLE_CREATION,
        'name': {"en": "Example Action"},
        'description': {"en": "This is an example action"},
        'description_is_markdown': False,
        'short_description': {},
        'short_description_is_markdown': False,
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
    r = requests.get(flask_server.base_url + 'api/v2/actions/', auth=auth)
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
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v2/actions/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'action_id': action.id,
            'instrument_id': None,
            'user_id': auth_user[1].id,
            'type': 'sample',
            'type_id': sampledb.models.ActionType.SAMPLE_CREATION,
            'name': {"en": "Example Action"},
            'description': {"en": "This is an example action"},
            'description_is_markdown': False,
            'short_description': {},
            'short_description_is_markdown': False,
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


def test_put_action(flask_server, auth):
    flask.current_app.config["SERVER_NAME"] = "localhost"
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
    r = requests.get(flask_server.base_url + 'api/v2/actions/{}'.format(action.id), auth=auth)
    assert r.status_code == 200

    action_data = r.json()

    r = requests.put(flask_server.base_url + f'api/v2/actions/{action.id + 1}', auth=auth, json=action_data)
    assert r.status_code == 404
    assert r.json() == {
        "detail": f"Action #{action.id + 1} does not exist.",
        "errors": [],
        "status": 404,
        "title": "The action does not exist.",
        "type": "http://localhost/api/v2/errors/ActionNotFound",
    }

    r = requests.put(flask_server.base_url + 'api/v2/actions/{}'.format(action.id), auth=auth, json=action_data)
    assert r.status_code == 403

    action_data['name'] = {"en": "Updated Example Action", "de": "Aktualisierte Beispiel-Aktion"}
    action_data['description'] = {"en": "This is an updated example action"}
    action_data['short_description'] = {"en": "*English* short description", "de": "*German* short description"}
    action_data['short_description_is_markdown'] = True
    action_data['is_hidden'] = True
    action_data['schema']['title'] = 'Updated Example Object'

    german = sampledb.logic.languages.get_language_by_lang_code('de')
    sampledb.logic.languages.update_language(
        language_id=german.id,
        names=german.names,
        lang_code=german.lang_code,
        datetime_format_datetime=german.datetime_format_datetime,
        datetime_format_moment=german.datetime_format_moment,
        datetime_format_moment_output=german.datetime_format_moment_output,
        date_format_moment_output=german.date_format_moment_output,
        enabled_for_input=False,
        enabled_for_user_interface=False,
    )

    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.GRANT)
    r = requests.put(flask_server.base_url + 'api/v2/actions/{}'.format(action.id), auth=auth)
    assert r.status_code == 400

    r = requests.put(flask_server.base_url + 'api/v2/actions/{}'.format(action.id), auth=auth, json=action_data)
    assert r.status_code == 400

    sampledb.logic.languages.update_language(
        language_id=german.id,
        names=german.names,
        lang_code=german.lang_code,
        datetime_format_datetime=german.datetime_format_datetime,
        datetime_format_moment=german.datetime_format_moment,
        datetime_format_moment_output=german.datetime_format_moment_output,
        date_format_moment_output=german.date_format_moment_output,
        enabled_for_input=True,
        enabled_for_user_interface=False,
    )
    r = requests.put(flask_server.base_url + 'api/v2/actions/{}'.format(action.id), auth=auth, json=action_data)
    assert r.status_code == 200
    assert r.json() == {
        'action_id': action.id,
        'instrument_id': None,
        'user_id': None,
        'type': 'sample',
        'type_id': sampledb.models.ActionType.SAMPLE_CREATION,
        'name': {"en": "Updated Example Action", "de": "Aktualisierte Beispiel-Aktion"},
        'description': {"en": "This is an updated example action"},
        'description_is_markdown': False,
        'short_description':  {"en": "*English* short description", "de": "*German* short description"},
        'short_description_is_markdown': True,
        'is_hidden': True,
        'schema': {
            'title': 'Updated Example Object',
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
    action = sampledb.logic.actions.get_action(action.id)
    assert action.name['en'] == "Updated Example Action"
    assert action.description['en'] == "This is an updated example action"
    assert action.is_hidden is True
    assert action.schema == {
        'title': 'Updated Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Object Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }

    action_data = r.json()
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.GRANT)
    for key, value in [
        ('action_id', action.id + 1),
        ('name', 'Example Action'),
        ('description', 'Example Description'),
        ('short_description', 'Example Short Description'),
        ('short_description_is_markdown', 'Markdown'),
        ('is_hidden', None),
        ('schema', [action.schema]),
        ('schema', {'title': 'Invalid Schema', 'type': 'object'}),
        ('description', {"en": "Example Description", "te": "Example Description"}),
        ('name', {"en": ""}),
        ('name', {"en": "x" * 101})
    ]:
        r = requests.put(flask_server.base_url + 'api/v2/actions/{}'.format(action.id), auth=auth, json={**action_data, key: value})
        assert r.status_code == 400, f"got status code {r.status_code} for: {key} -> {value}"
