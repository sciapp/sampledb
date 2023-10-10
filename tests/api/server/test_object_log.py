# coding: utf-8
"""

"""

import requests
import pytest

import sampledb
import sampledb.logic
import sampledb.models
from sampledb.logic.objects import create_object


@pytest.fixture
def auth_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
        assert user.id is not None
    return ('username', 'password'), user


@pytest.fixture
def auth_user2(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User 2", email="example2@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username2', 'password')
        assert user.id is not None
    return ('username2', 'password'), user


@pytest.fixture
def auth(auth_user):
    return auth_user[0]


@pytest.fixture
def user(auth_user):
    return auth_user[1]


@pytest.fixture
def auth2(auth_user2):
    return auth_user2[0]


@pytest.fixture
def user2(auth_user2):
    return auth_user2[1]


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
    return action


@pytest.fixture
def object(user, action):
    object = create_object(user_id=user.id, action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    return object


def test_get_object_log_entries(flask_server, auth, auth2, user, user2, object, action, app):
    r = requests.get(flask_server.base_url + 'api/v1/object_log_entries/', auth=auth2)
    entries = r.json()
    assert entries == []  # user2 has no read access
    r = requests.get(flask_server.base_url + 'api/v1/object_log_entries/', auth=auth)
    entries = r.json()
    assert len(entries) == 1    # only object creation
    local_entry = sampledb.logic.object_log.get_object_log_entries(object.object_id, object.user_id)[0]
    assert local_entry.id == entries[0]['log_entry_id']
    assert local_entry.type.name == entries[0]['type']
    assert local_entry.object_id == entries[0]['object_id']
    assert local_entry.user_id == entries[0]['user_id']
    assert local_entry.data == entries[0]['data']
    assert local_entry.utc_datetime.strftime('%Y-%m-%d %H:%M:%S') == entries[0]['utc_datetime']
    r = requests.get(flask_server.base_url + 'api/v1/object_log_entries/', params={'after_id': local_entry.id}, auth=auth)
    entries = r.json()
    assert entries == []  # There is no object log_entry > 1
    sampledb.logic.comments.create_comment(object.id, object.user_id, content='Comment')
    r = requests.get(flask_server.base_url + 'api/v1/object_log_entries/', auth=auth)
    entries = r.json()
    assert len(entries) == 2    # object creation and comment
    local_entries = sampledb.logic.object_log.get_object_log_entries(object.object_id, object.user_id)
    for entry, local_entry in zip(entries, local_entries):
        assert local_entry.id == entry['log_entry_id']
        assert local_entry.type.name == entry['type']
        assert local_entry.object_id == entry['object_id']
        assert local_entry.user_id == entry['user_id']
        assert local_entry.data == entry['data']
        assert local_entry.utc_datetime.strftime('%Y-%m-%d %H:%M:%S') == entry['utc_datetime']
    object2 = create_object(user_id=user2.id, action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    r = requests.get(flask_server.base_url + 'api/v1/object_log_entries/', auth=auth)
    entries = r.json()
    assert len(entries) == 2    # new object by other user should not affect this result...
    r = requests.get(flask_server.base_url + 'api/v1/object_log_entries/', auth=auth2)
    entries = r.json()
    assert len(entries) == 1
    local_entry = sampledb.logic.object_log.get_object_log_entries(object2.object_id, user2.id)[0]
    assert local_entry.id == entries[0]['log_entry_id']
    assert local_entry.type.name == entries[0]['type']
    assert local_entry.object_id == entries[0]['object_id']
    assert local_entry.user_id == entries[0]['user_id']
    assert local_entry.data == entries[0]['data']
    assert local_entry.utc_datetime.strftime('%Y-%m-%d %H:%M:%S') == entries[0]['utc_datetime']   # ...but user2 is allowed to read it
    sampledb.logic.users.set_user_administrator(user2.id, True)
    sampledb.logic.settings.set_user_settings(user2.id, {'USE_ADMIN_PERMISSIONS': True})
    r = requests.get(flask_server.base_url + 'api/v1/object_log_entries/', auth=auth2)
    entries = r.json()
    assert len(entries) == 3  # user2 became admin and is able to access all object log entries...
    r = requests.get(flask_server.base_url + 'api/v1/object_log_entries/', params={'after_id': local_entry.id - 1}, auth=auth2)
    entries = r.json()
    assert len(entries) == 1  # ...but filters the results
