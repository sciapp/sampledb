# coding: utf-8
"""

"""
import datetime
import time

import requests
import secrets

import sampledb
import sampledb.logic
import sampledb.models


def test_authentication_ldap(flask_server):
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=(flask_server.app.config['TESTING_LDAP_LOGIN'], flask_server.app.config['TESTING_LDAP_PW']))
    assert r.status_code == 200


def test_authentication_email(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_email_authentication(user.id, 'example@example.com', 'password')
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=('example@example.com', 'password'))
    assert r.status_code == 200


def test_authentication_other(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=('username', 'password'))
    assert r.status_code == 200


def test_authentication_token(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        api_token = secrets.token_hex(32)
        sampledb.logic.authentication.add_api_token(user.id, api_token, 'Demo API Token')
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', headers={'Authorization': 'Bearer ' + api_token})
    assert r.status_code == 200


def test_authentication_inactive_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
        user_id = user.id
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=('username', 'password'))
    assert r.status_code == 200
    with flask_server.app.app_context():
        sampledb.logic.users.set_user_active(user_id, False)
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=('username', 'password'))
    assert r.status_code == 401
    with flask_server.app.app_context():
        sampledb.logic.users.set_user_active(user_id, True)
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=('username', 'password'))
    assert r.status_code == 200


def test_authentication_access_token(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        api_token = secrets.token_hex(32)
        sampledb.logic.authentication.add_api_token(user.id, api_token, 'Demo API Token')
    r = requests.post(flask_server.base_url + 'api/v1/access_tokens/', json={'description': 'API Session Token Test'})
    assert r.status_code == 401
    r = requests.post(flask_server.base_url + 'api/v1/access_tokens/', headers={'Authorization': 'Bearer ' + api_token})
    assert r.status_code == 400
    r = requests.post(flask_server.base_url + 'api/v1/access_tokens/', headers={'Authorization': 'Bearer ' + api_token}, json=[])
    assert r.status_code == 400
    r = requests.post(flask_server.base_url + 'api/v1/access_tokens/', headers={'Authorization': 'Bearer ' + api_token}, json={})
    assert r.status_code == 400
    r = requests.post(flask_server.base_url + 'api/v1/access_tokens/', headers={'Authorization': 'Bearer ' + api_token}, json={'description': None})
    assert r.status_code == 400
    r = requests.post(flask_server.base_url + 'api/v1/access_tokens/', headers={'Authorization': 'Bearer ' + api_token}, json={'description': 'API Session Token Test'})
    assert r.status_code == 201
    response_json = r.json()
    assert isinstance(response_json['access_token'], str)
    assert isinstance(response_json['refresh_token'], str)
    assert response_json['description'] == 'API Session Token Test'
    expiration_utc_datetime = datetime.datetime.strptime(response_json['expiration_utc_datetime'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
    assert datetime.datetime.now(datetime.timezone.utc) < expiration_utc_datetime <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    access_token = response_json['access_token']
    refresh_token = response_json['refresh_token']
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', headers={'Authorization': 'Bearer ' + access_token})
    assert r.status_code == 200
    # refresh token cannot be used to access the API
    r = requests.get(flask_server.base_url + 'api/v1/objects/', headers={'Authorization': 'Bearer ' + refresh_token})
    assert r.status_code == 401
    # access token cannot be used to create new access tokens
    r = requests.post(flask_server.base_url + 'api/v1/access_tokens/', headers={'Authorization': 'Bearer ' + access_token}, json={'description': 'API Session Token Test'})
    assert r.status_code == 401
    # wait 1 second to test that expiration datetime will actually change during refresh
    time.sleep(1)
    r = requests.post(flask_server.base_url + 'api/v1/access_tokens/', headers={'Authorization': 'Bearer ' + refresh_token})
    assert r.status_code == 201
    response_json = r.json()
    assert isinstance(response_json['access_token'], str)
    assert isinstance(response_json['refresh_token'], str)
    assert response_json['description'] == 'API Session Token Test'
    previous_expiration_utc_datetime = expiration_utc_datetime
    expiration_utc_datetime = datetime.datetime.strptime(response_json['expiration_utc_datetime'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
    assert previous_expiration_utc_datetime < expiration_utc_datetime <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
