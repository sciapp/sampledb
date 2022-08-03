import datetime
import secrets
import time

import flask
import requests

import sampledb
from sampledb import logic
from sampledb.logic.component_authentication import add_token_authentication
from sampledb.logic.components import add_component
from sampledb.logic.users import create_user_alias

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'


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

        ts1 = datetime.datetime.utcnow()
        time.sleep(0.1)
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
        ts2 = datetime.datetime.utcnow()
        time.sleep(0.1)
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
        time.sleep(0.1)
        ts3 = datetime.datetime.utcnow()

    headers = {
        'Authorization': 'Bearer ' + token
    }

    # no last sync
    ts_before_sync = datetime.datetime.utcnow()
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers)
    ts_after_sync = datetime.datetime.utcnow()
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == [alias_data_1, alias_data_2, alias_data_3]
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.PROTOCOL_VERSION_MINOR
    }
    assert ts_before_sync <= datetime.datetime.strptime(result['header']['sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f') <= ts_after_sync

    parameters = {
        'last_sync_timestamp': ts1.strftime('%Y-%m-%d %H:%M:%S.%f')
    }
    ts_before_sync = datetime.datetime.utcnow()
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers, params=parameters)
    ts_after_sync = datetime.datetime.utcnow()
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == [alias_data_1, alias_data_2, alias_data_3]
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.PROTOCOL_VERSION_MINOR
    }
    assert ts_before_sync <= datetime.datetime.strptime(result['header']['sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f') <= ts_after_sync

    parameters = {
        'last_sync_timestamp': ts2.strftime('%Y-%m-%d %H:%M:%S.%f')
    }
    ts_before_sync = datetime.datetime.utcnow()
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers, params=parameters)
    ts_after_sync = datetime.datetime.utcnow()
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == [alias_data_2, alias_data_3]
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.PROTOCOL_VERSION_MINOR
    }
    assert ts_before_sync <= datetime.datetime.strptime(result['header']['sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f') <= ts_after_sync

    parameters = {
        'last_sync_timestamp': ts3.strftime('%Y-%m-%d %H:%M:%S.%f')
    }
    ts_before_sync = datetime.datetime.utcnow()
    r = requests.get(flask_server.base_url + 'federation/v1/shares/users/', headers=headers, params=parameters)
    ts_after_sync = datetime.datetime.utcnow()
    assert r.status_code == 200
    result = r.json()
    assert result['users'] == []
    assert result['header']['db_uuid'] == uuid
    assert result['header']['target_uuid'] == component.uuid
    assert result['header']['protocol_version'] == {
        'major': logic.federation.PROTOCOL_VERSION_MAJOR,
        'minor': logic.federation.PROTOCOL_VERSION_MINOR
    }
    assert ts_before_sync <= datetime.datetime.strptime(result['header']['sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f') <= ts_after_sync
