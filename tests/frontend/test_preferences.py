# coding: utf-8
"""

"""

import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models


from tests.test_utils import flask_server, app

@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user



def test_user_preferences(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'username', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'password', 'type': 'password'}) is not None
    assert document.find('input', {'name': 'remember_me', 'type': 'checkbox'}) is not None
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': False,
        'csrf_token': csrf_token
    })

    assert r.status_code == 200

    r = session.get(flask_server.base_url + 'users/me/preferences')
    assert r.status_code == 200
    assert document.find('input', {'name': 'name', 'type': 'text'}) is None
    assert document.find('input', {'name': 'email', 'type': 'text'}) is  None

def test_user_preferences_userid_wrong(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'username', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'password', 'type': 'password'}) is not None
    assert document.find('input', {'name': 'remember_me', 'type': 'checkbox'}) is not None
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': False,
        'csrf_token': csrf_token
    })

    assert r.status_code == 200

    r = session.get(flask_server.base_url + 'users/10/preferences')
    assert r.status_code == 403

def test_user_preferences_change_name(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'username', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'password', 'type': 'password'}) is not None
    assert document.find('input', {'name': 'remember_me', 'type': 'checkbox'}) is not None
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': False,
        'csrf_token': csrf_token
    })

    assert r.status_code == 200

    r = session.get(flask_server.base_url + 'users/me/preferences')
    url = flask_server.base_url + 'users/me/preferences'
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    # Submit the missing information and complete the registration
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'name': 'Doro Testaccount1111',
            'email': 'd.henkel@fz-juelich.de',
            'csrf_token': csrf_token
        })

    assert r.status_code == 200

def test_user_preferences_change_contactemail(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'username', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'password', 'type': 'password'}) is not None
    assert document.find('input', {'name': 'remember_me', 'type': 'checkbox'}) is not None
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': False,
        'csrf_token': csrf_token
    })

    assert r.status_code == 200

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith(flask_server.base_url + 'users/')
    assert r.headers['Location'].endswith('/preferences')
    url = r.headers['Location']

    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'name', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'email', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'name', 'type': 'text'})["value"] != ""
    assert document.find('input', {'name': 'email', 'type': 'text'})["value"] != ""

    # Send a POST request to the confirmation url
    # TODO: require authorization
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']

    # Submit the missing information and complete the registration
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'name': 'Doro Testaccount1',
            'email': 'example@fz-juelich.de',
            'csrf_token': csrf_token
        })
        assert r.status_code == 200

    # Check if an invitation mail was sent
    assert len(outbox) == 1
    assert 'example@fz-juelich.de' in outbox[0].recipients
    message = outbox[0].html
    assert 'Welcome to iffsample!' in message

    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[1].split('"')[0]
    assert confirmation_url.startswith(flask_server.base_url + 'confirm-email')
    r = session.get(confirmation_url)
    assert r.status_code == 200
