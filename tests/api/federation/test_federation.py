import datetime
import secrets
import time

import flask
import requests
import pytest

import sampledb
from sampledb import logic
from sampledb import models
from sampledb.logic import shares, actions, objects, component_authentication, components, files
from sampledb.logic.component_authentication import add_token_authentication
from sampledb.logic.components import add_component
from sampledb.logic.users import create_user_alias

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'


@pytest.fixture
def user(flask_server):
    user = models.User(name='User', email="example@example.com", type=models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


@pytest.fixture
def action():
    action = actions.create_action(
        action_type_id=models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        instrument_id=None
    )
    return action


@pytest.fixture
def simple_object(user, action):
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    return objects.create_object(user_id=user.id, action_id=action.id, data=data)


@pytest.fixture
def component_token():
    token = 'a' * 64
    component = components.add_component(UUID_1, 'TestDB', None, '')
    component_authentication.add_token_authentication(component.id, token, '')
    return component, token


def test_get_users(flask_server):
    with flask_server.app.app_context():
        uuid = flask.current_app.config['FEDERATION_UUID']
        component = add_component(address=None, uuid=UUID_1, name='Example component', description='')
        token = secrets.token_hex(32)
        description = 'Token'
        add_token_authentication(component.id, token, description)

        user1 = sampledb.models.User(name="Basic User 1", email="example1@example.com", type=sampledb.models.UserType.PERSON)
        user2 = sampledb.models.User(name="Basic User 2", email="example1@example.com", type=sampledb.models.UserType.PERSON)
        user3 = sampledb.models.User(name="Basic User 3", email="example1@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user1)
        sampledb.db.session.add(user2)
        sampledb.db.session.add(user3)
        sampledb.db.session.commit()

        ts1 = datetime.datetime.now(datetime.timezone.utc)
        time.sleep(0.01)
        alias_user1 = create_user_alias(user1.id, component.id, 'B. User 1', False, None, False, None, False, None, False, None, False)
        alias_data_1 = {
            'user_id': alias_user1.user_id,
            'component_uuid': uuid,
            'name': alias_user1.name,
            'email': alias_user1.email,
            'orcid': alias_user1.orcid,
            'affiliation': alias_user1.affiliation,
            'role': alias_user1.role,
            'extra_fields': alias_user1.extra_fields
        }
        time.sleep(0.01)
        ts2 = datetime.datetime.now(datetime.timezone.utc)
        alias_user2 = create_user_alias(user2.id, component.id, None, False, None, False, None, False, None, False, None, False)
        alias_data_2 = {
            'user_id': alias_user2.user_id,
            'component_uuid': uuid,
            'name': alias_user2.name,
            'email': alias_user2.email,
            'orcid': alias_user2.orcid,
            'affiliation': alias_user2.affiliation,
            'role': alias_user2.role,
            'extra_fields': alias_user2.extra_fields
        }
        alias_user3 = create_user_alias(user3.id, component.id, 'B. User 3', False, None, False, None, False, None, False, None, False)
        alias_data_3 = {
            'user_id': alias_user3.user_id,
            'component_uuid': uuid,
            'name': alias_user3.name,
            'email': alias_user3.email,
            'orcid': alias_user3.orcid,
            'affiliation': alias_user3.affiliation,
            'role': alias_user3.role,
            'extra_fields': alias_user3.extra_fields
        }
        time.sleep(0.01)
        ts3 = datetime.datetime.now(datetime.timezone.utc)

    headers = {
        'Authorization': 'Bearer ' + token
    }

    # no last sync
    ts_before_sync = datetime.datetime.now(datetime.timezone.utc)
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers)
    ts_after_sync = datetime.datetime.now(datetime.timezone.utc)
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == [alias_data_1, alias_data_2, alias_data_3]
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.update.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.update.PROTOCOL_VERSION_MINOR
    }
    assert ts_before_sync <= datetime.datetime.strptime(result['header']['sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f') <= ts_after_sync

    parameters = {
        'last_sync_timestamp': ts1.strftime('%Y-%m-%d %H:%M:%S.%f')
    }
    ts_before_sync = datetime.datetime.now(datetime.timezone.utc)
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers, params=parameters)
    ts_after_sync = datetime.datetime.now(datetime.timezone.utc)
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == [alias_data_1, alias_data_2, alias_data_3]
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.update.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.update.PROTOCOL_VERSION_MINOR
    }
    assert ts_before_sync <= datetime.datetime.strptime(result['header']['sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f') <= ts_after_sync

    parameters = {
        'last_sync_timestamp': ts2.strftime('%Y-%m-%d %H:%M:%S.%f')
    }
    ts_before_sync = datetime.datetime.now(datetime.timezone.utc)
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers, params=parameters)
    ts_after_sync = datetime.datetime.now(datetime.timezone.utc)
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == [alias_data_2, alias_data_3]
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.update.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.update.PROTOCOL_VERSION_MINOR
    }
    assert ts_before_sync <= datetime.datetime.strptime(result['header']['sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f') <= ts_after_sync

    parameters = {
        'last_sync_timestamp': ts3.strftime('%Y-%m-%d %H:%M:%S.%f')
    }
    ts_before_sync = datetime.datetime.now(datetime.timezone.utc)
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers, params=parameters)
    ts_after_sync = datetime.datetime.now(datetime.timezone.utc)
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == []
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.update.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.update.PROTOCOL_VERSION_MINOR
    }
    assert ts_before_sync <= datetime.datetime.strptime(result['header']['sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f') <= ts_after_sync

    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers)
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == [alias_data_1, alias_data_2, alias_data_3]

    sampledb.logic.users.set_user_hidden(alias_data_1['user_id'], True)
    sampledb.logic.users.set_user_active(alias_data_2['user_id'], False)
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers)
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == [alias_data_3]


def test_file_resource_database(flask_server, simple_object, user, component_token):
    component, token = component_token
    database_file = files.create_database_file(simple_object.object_id, user.id, 'testfile.txt', lambda stream: stream.write(b'testcontent'))
    shares.add_object_share(database_file.object_id, component.id, {'access': {'files': True}})

    headers = {'Authorization': 'Bearer  {}'.format(token)}
    r = requests.get(flask_server.base_url + 'federation/v1/shares/objects/{}/files/{}'.format(database_file.object_id, database_file.id), headers=headers)
    assert r.status_code == 200
    assert r.headers['Content-Disposition'] == 'attachment; filename={}'.format(database_file.original_file_name)
    with database_file.open() as f:
        assert r.content == f.read()


def test_file_resource_local(flask_server, simple_object, user, component_token):
    component, token = component_token
    local_file = files.create_local_file(simple_object.object_id, user.id, 'testfile.txt', lambda stream: stream.write(b'testcontent'))
    shares.add_object_share(local_file.object_id, component.id, {'access': {'files': True}})

    headers = {'Authorization': 'Bearer  {}'.format(token)}
    r = requests.get(flask_server.base_url + 'federation/v1/shares/objects/{}/files/{}'.format(local_file.object_id, local_file.id), headers=headers)
    assert r.status_code == 200
    assert r.headers['Content-Disposition'] == 'attachment; filename={}'.format(local_file.original_file_name)
    with local_file.open() as f:
        assert r.content == f.read()


def test_file_resource_url(flask_server, simple_object, user, component_token):
    uuid = flask.current_app.config['FEDERATION_UUID']
    component, token = component_token
    url_file = files.create_url_file(simple_object.object_id, user.id, 'www.example.com')
    shares.add_object_share(url_file.object_id, component.id, {'access': {'files': True}})

    headers = {'Authorization': 'Bearer  {}'.format(token)}
    r = requests.get(flask_server.base_url + 'federation/v1/shares/objects/{}/files/{}'.format(url_file.object_id, url_file.id), headers=headers)
    assert r.status_code == 200
    result = r.json()
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.update.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.update.PROTOCOL_VERSION_MINOR
    }
    assert result['object_id'] == url_file.object_id
    assert result['file_id'] == url_file.id
    assert result['storage'] == 'url'
    assert result['url'] == url_file.url


def test_file_resource_errors(flask_server, simple_object, user, component_token):
    component, token = component_token
    database_file = files.create_database_file(simple_object.object_id, user.id, 'testfile.txt', lambda stream: stream.write(b'testcontent'))
    headers = {'Authorization': 'Bearer  {}'.format(token)}
    r = requests.get(flask_server.base_url + 'federation/v1/shares/objects/{}/files/{}'.format(database_file.object_id, database_file.id))
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'federation/v1/shares/objects/{}/files/{}'.format(database_file.object_id + 1, database_file.id), headers=headers)
    assert r.status_code == 404
    assert r.json() == {"message": "object {} does not exist".format(database_file.object_id + 1)}
    r = requests.get(flask_server.base_url + 'federation/v1/shares/objects/{}/files/{}'.format(database_file.object_id, database_file.id), headers=headers)
    assert r.status_code == 403
    assert r.json() == {"message": "object {} is not shared".format(database_file.object_id)}
    shares.add_object_share(database_file.object_id, component.id, {})
    r = requests.get(flask_server.base_url + 'federation/v1/shares/objects/{}/files/{}'.format(database_file.object_id, database_file.id), headers=headers)
    assert r.status_code == 403
    assert r.json() == {"message": "files linked to object {} are not shared".format(database_file.object_id)}
    shares.update_object_share(database_file.object_id, component.id, {'access': {'files': False}})
    r = requests.get(flask_server.base_url + 'federation/v1/shares/objects/{}/files/{}'.format(database_file.object_id, database_file.id), headers=headers)
    assert r.status_code == 403
    assert r.json() == {"message": "files linked to object {} are not shared".format(database_file.object_id)}


def test_import_status(flask_server, component_token, simple_object, user):
    component, token = component_token
    shares.add_object_share(simple_object.id, component.id, {'access': {'objects': True}}, user.id)

    import_status_data = {
        'success': True,
        'notes': [],
        'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        'object_id': 42
    }
    headers = {'Authorization': 'Bearer  {}'.format(token)}

    r = requests.put(
        flask_server.base_url + f'federation/v1/shares/objects/{simple_object.id}/import_status',
        headers=headers
    )
    assert r.status_code == 400
    assert shares.get_share(simple_object.id, component.id).import_status is None

    r = requests.put(
        flask_server.base_url + f'federation/v1/shares/objects/{simple_object.id}/import_status',
        headers=headers,
        json={}
    )
    assert r.status_code == 400
    assert shares.get_share(simple_object.id, component.id).import_status is None

    r = requests.put(
        flask_server.base_url + f'federation/v1/shares/objects/{simple_object.id}/import_status',
        headers=headers,
        json=import_status_data
    )
    assert r.status_code == 204
    assert shares.get_share(simple_object.id, component.id).import_status == import_status_data
    last_fed_log_entry = logic.fed_logs.get_fed_object_log_entries_for_object(object_id=simple_object.id, component_id=component.id)[0]
    assert last_fed_log_entry.type == models.FedObjectLogEntryType.REMOTE_IMPORT_OBJECT
    assert last_fed_log_entry.data['import_status'] == import_status_data

    import_status_data['success'] = False
    import_status_data['notes'] = ['Error']
    r = requests.put(
        flask_server.base_url + f'federation/v1/shares/objects/{simple_object.id}/import_status',
        headers=headers,
        json=import_status_data
    )
    assert r.status_code == 400
    assert shares.get_share(simple_object.id, component.id).import_status != import_status_data
    last_fed_log_entry = logic.fed_logs.get_fed_object_log_entries_for_object(object_id=simple_object.id, component_id=component.id)[0]
    assert last_fed_log_entry.type == models.FedObjectLogEntryType.REMOTE_IMPORT_OBJECT
    assert last_fed_log_entry.data['import_status'] != import_status_data

    import_status_data['object_id'] = None
    r = requests.put(
        flask_server.base_url + f'federation/v1/shares/objects/{simple_object.id}/import_status',
        headers=headers,
        json=import_status_data
    )
    assert r.status_code == 204
    assert shares.get_share(simple_object.id, component.id).import_status == import_status_data
    last_fed_log_entry = logic.fed_logs.get_fed_object_log_entries_for_object(object_id=simple_object.id, component_id=component.id)[0]
    assert last_fed_log_entry.type == models.FedObjectLogEntryType.REMOTE_IMPORT_OBJECT
    assert last_fed_log_entry.data['import_status'] == import_status_data
    notifications = logic.notifications.get_notifications(user_id=user.id, unread_only=True)
    assert len(notifications) == 1
    assert notifications[0].type == models.NotificationType.REMOTE_OBJECT_IMPORT_FAILED
    assert notifications[0].data == {
        'object_id': simple_object.id,
        'component_id': component.id
    }

    r = requests.put(
        flask_server.base_url + f'federation/v1/shares/objects/{simple_object.id + 1}/import_status',
        headers=headers,
        json=import_status_data
    )
    assert r.status_code == 404
