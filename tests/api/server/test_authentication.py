# coding: utf-8
"""

"""

import requests
import secrets

import sampledb
import sampledb.logic
import sampledb.models


from tests.test_utils import flask_server, app


def test_authentication_ldap(flask_server):
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=(flask_server.app.config['TESTING_LDAP_LOGIN'], flask_server.app.config['TESTING_LDAP_PW']))
    assert r.status_code == 200


def test_authentication_email(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_email_authentication(user.id, 'example@fz-juelich.de', 'password')
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=('example@fz-juelich.de', 'password'))
    assert r.status_code == 200


def test_authentication_other(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=('username', 'password'))
    assert r.status_code == 200


def test_authentication_token(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        api_token = secrets.token_hex(32)
        sampledb.logic.authentication.add_api_token(user.id, api_token, 'Demo API Token')
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    r = requests.get(flask_server.base_url + 'api/v1/objects/', headers={'Authorization': 'Bearer ' + api_token})
    assert r.status_code == 200

