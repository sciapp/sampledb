# coding: utf-8
"""

"""
import secrets

import flask
import requests
import pytest
import pyotp
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import visibility_of_element_located

import sampledb
import sampledb.models
import sampledb.logic
from sampledb.logic.authentication import add_email_authentication
from sampledb.logic import object_permissions, default_permissions, groups, projects

from ..conftest import wait_for_page_load


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        add_email_authentication(user.id, 'example@example.com', 'abc.123', True)
        # force attribute refresh
        assert user.id is not None
        # Check if authentication-method add to db
        with flask_server.app.app_context():
            assert len(sampledb.models.Authentication.query.all()) == 1
    return user


def test_user_preferences(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'username', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'password', 'type': 'password'}) is not None
    assert document.find('input', {'name': 'remember_me', 'type': 'hidden'}) is not None
    assert document.find('input', {'name': 'shared_device', 'type': 'hidden'}) is not None
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': '',
        'shared_device': 'shared_device',
        'csrf_token': csrf_token
    })

    assert r.status_code == 200

    r = session.get(flask_server.base_url + 'users/me/preferences')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'name', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'email', 'type': 'text'}) is not None
    assert document.find('span', {'id': 'session-timeout-marker'}) is not None


def test_user_preferences_userid_wrong(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    r = session.get(f'{flask_server.base_url}users/{user.id + 1}/preferences')
    assert r.status_code == 403


def test_user_preferences_change_name(flask_server, user):
    # Try logging in with ldap-test-account
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200

    with flask_server.app.app_context():
        user = sampledb.models.users.User.query.filter_by(email="example@example.com").one()

    assert user.name == "Basic User"

    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']

    # Submit the missing information and complete the registration
    r = session.post(url, {
        'name': 'Testaccount',
        'email': 'example@example.com',
        'csrf_token': csrf_token,
        'change': 'Change'
    })
    # check, if name was changed
    assert r.status_code == 200
    with flask_server.app.app_context():
        user = sampledb.models.users.User.query.filter_by(email="example@example.com").first()

    assert user is not None
    assert user.name == "Testaccount"


def test_user_preferences_change_contactemail(flask_server, user):
    # Try logging in with ldap-test-account
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True
    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]

    user_id = int(url[len(flask_server.base_url + 'users/'):].split('/')[0])

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
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user_id) == []
    # Submit the missing information and complete the registration
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'name': 'Basic User',
            'email': 'user@example.com',
            'csrf_token': csrf_token,
            'change': 'Change'
        })
        assert r.status_code == 200

    # Check if an invitation mail was sent
    assert len(outbox) == 1
    assert 'user@example.com' in outbox[0].recipients
    message = outbox[0].html
    assert 'SampleDB Email Confirmation' in message

    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user_id) == []

    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[2].split('"')[0]
    assert confirmation_url.startswith(f'{flask_server.base_url}users/{user_id}/preferences')
    r = session.get(confirmation_url)

    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user_id)
        assert len(user_log_entries) == 1
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.EDIT_USER_PREFERENCES
        assert user_log_entries[0].user_id == user_id
        assert user_log_entries[0].data == {}
    assert r.status_code == 200

    # check, if email was changed after open confirmation_url
    with flask_server.app.app_context():
        user = sampledb.models.users.User.query.filter_by(email="user@example.com").first()

    assert user is not None


def test_user_add_ldap_authentication_method_wrong_password(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True
    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    #  add ldap-account , password wrong
    r = session.post(url, {
        'login': 'username',
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'authentication_method': 'L',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200
    assert 'Ldap login or password wrong' in r.content.decode('utf-8')


def test_user_add_ldap_authentication_method(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True
    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200

    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 1

    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    #  add ldap-account
    r = session.post(url, {
        'login': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'authentication_method': 'L',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200

    # Check if authentication-method add to db
    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 2
        authentication_method = sampledb.models.Authentication.query.filter_by(type=sampledb.models.AuthenticationType.LDAP).first()
        assert authentication_method.login['login'] == flask_server.app.config['TESTING_LDAP_LOGIN']


def test_user_add_ldap_authentication_method_case_insensitive(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True
    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200

    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 1

    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    #  add ldap-account
    r = session.post(url, {
        'login': flask_server.app.config['TESTING_LDAP_LOGIN'].upper(),
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'authentication_method': 'L',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200

    # Check if authentication-method add to db
    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 2
        authentication_method = sampledb.models.Authentication.query.filter_by(type=sampledb.models.AuthenticationType.LDAP).first()
        assert authentication_method.login['login'] == flask_server.app.config['TESTING_LDAP_LOGIN']


def test_user_add_other_authentication_method_not_allowed(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True
    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200

    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 1

    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    #  add ldap-account
    r = session.post(url, {
        'login': 'experiment',
        'password': 'test',
        'authentication_method': 'O',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200

    # Check if authentication-method not add to db
    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 1


def test_user_add_general_authentication_method(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'username', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'password', 'type': 'password'}) is not None
    assert document.find('input', {'name': 'remember_me', 'type': 'hidden'}) is not None
    assert document.find('input', {'name': 'shared_device', 'type': 'hidden'}) is not None
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': '',
        'shared_device': '',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form

    #  add authentication_method with password is to short
    r = session.post(url, {
        'login': 'test',
        'password': 'xx',
        'authentication_method': 'L',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200
    assert 'The password must be at least 3 characters long' in r.content.decode('utf-8')

    #  add identically authentication_method
    r = session.post(url, {
        'login': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'authentication_method': 'L',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200
    assert 'An authentication method with this login already exists' in r.content.decode('utf-8')

    #  add ldap-account , second ldap account not possible
    r = session.post(url, {
        'login': 'username',
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'authentication_method': 'L',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200
    assert 'An LDAP-based authentication method already exists for this user' in r.content.decode('utf-8')

    #  add authentication-email without email
    r = session.post(url, {
        'login': 'web.de',
        'password': 'xxxx',
        'authentication_method': 'E',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200
    assert 'Login must be a valid email address' in r.content.decode('utf-8')


def test_user_add_email_authentication_method(flask_server, user):
    # Try logging in with ldap-test-account
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]

    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form

    #  add valid email authentication-method
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'login': 'user@example.com',
            'password': 'abc.123',
            'authentication_method': 'E',
            'csrf_token': csrf_token,
            'add': 'Add'
        })
    assert r.status_code == 200

    # Check if an confirmation mail was sent
    assert len(outbox) == 1
    assert 'user@example.com' in outbox[0].recipients
    message = outbox[0].html
    assert 'SampleDB Email Confirmation' in message

    # Check if authentication-method add to db
    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 2

    # Create new session
    session = requests.session()

    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    # initially, the a link to the sign in page will be displayed
    r = session.get(flask_server.base_url)
    assert r.status_code == 200
    assert '/users/me/sign_in' in r.content.decode('utf-8')
    # Try to login
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': 'user@example.com',
        'password': 'abc.123',
        'remember_me': False,
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # expect False, user is not confirmed
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False

    # login again with Basic User
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True
    # Get the confirmation url from the mail and open it
    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[2].split('"')[0]
    assert confirmation_url.startswith(f'{flask_server.base_url}users/{user.id}/preferences')
    r = session.get(confirmation_url)
    assert r.status_code == 200

    # initially, the a link to the preferences page will be displayed
    r = session.get(flask_server.base_url)
    assert r.status_code == 200
    assert f'/users/{user.id}/preferences' in r.content.decode('utf-8')
    # Try to login
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': 'user@example.com',
        'password': 'abc.123',
        'remember_me': False,
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # expect True, user is confirmed
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True


def test_user_add_email_authentication_method_already_exists(flask_server, user):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'username', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'password', 'type': 'password'}) is not None
    assert document.find('input', {'name': 'remember_me', 'type': 'hidden'}) is not None
    assert document.find('input', {'name': 'shared_device', 'type': 'hidden'}) is not None
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': '',
        'shared_device': '',
        'csrf_token': csrf_token
    })

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]

    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form

    #  add valid email authentication-method
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'login': 'example@example.com',
            'password': 'abc.123',
            'authentication_method': 'E',
            'csrf_token': csrf_token,
            'add': 'Add'
        })
    assert r.status_code == 200
    # Check if an confirmation mail was not sent
    assert len(outbox) == 0
    assert 'An authentication method with this login already exists' in r.content.decode('utf-8')


def test_user_remove_authentication_method(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'username', 'type': 'text'}) is not None
    assert document.find('input', {'name': 'password', 'type': 'password'}) is not None
    assert document.find('input', {'name': 'remember_me', 'type': 'hidden'}) is not None
    assert document.find('input', {'name': 'shared_device', 'type': 'hidden'}) is not None
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': '',
        'shared_device': '',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]

    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form

    #  delete  authentication-method, only one exists
    r = session.post(url, {
        'id': str(sampledb.models.Authentication.query.first().id),
        'csrf_token': csrf_token,
        'remove': 'Remove'
    })
    assert r.status_code == 200
    assert 'one authentication-method must at least exist, delete not possible' in r.content.decode('utf-8')

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url =flask_server.base_url + r.headers['Location'][1:]
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form

    #  add authentication_method for testing remove
    r = session.post(url, {
        'login': 'user@example.com',
        'password': 'xxxxx',
        'authentication_method': 'E',
        'csrf_token': csrf_token,
        'add': 'Add'
    })
    assert r.status_code == 200

    # Check if authentication-method add to db
    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 2

    #  delete  authentication-method, two exist
    r = session.post(url, {
        'id': str(sampledb.models.Authentication.query.all()[1].id),
        'csrf_token': csrf_token,
        'remove': 'Remove'
    })
    assert r.status_code == 200

    # Check if authentication-method remove from db
    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 1


def test_edit_default_public_permissions(flask_server, user):
    with flask_server.app.app_context():
        assert sampledb.models.Permissions.READ not in default_permissions.get_default_permissions_for_all_users(user.id)

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/{}/preferences'.format(user.id))
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')

    default_permissions_form = document.find(attrs={'name': 'edit_permissions', 'value': 'edit_permissions'}).find_parent('form')

    data = {}
    for hidden_field in default_permissions_form.find_all('input', {'type': 'hidden'}):
        data[hidden_field['name']] = hidden_field['value']
    for radio_button in default_permissions_form.find_all('input', {'type': 'radio'}):
        if radio_button.has_attr('checked') and not radio_button.has_attr('disabled'):
            data[radio_button['name']] = radio_button['value']
    assert data['all_user_permissions'] == 'none'

    data['all_user_permissions'] = 'read'
    data['edit_permissions'] = 'edit_permissions'
    assert session.post(flask_server.base_url + 'users/{}/preferences'.format(user.id), data=data).status_code == 200

    with flask_server.app.app_context():
        assert sampledb.models.Permissions.READ in default_permissions.get_default_permissions_for_all_users(user.id)


def test_edit_default_user_permissions(flask_server, user):
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name="New User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
        default_permissions.set_default_permissions_for_user(creator_id=user.id, user_id=new_user_id, permissions=object_permissions.Permissions.WRITE)
        assert default_permissions.get_default_permissions_for_users(creator_id=user.id).get(new_user_id) == object_permissions.Permissions.WRITE

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/{}/preferences'.format(user.id))
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')

    default_permissions_form = document.find(attrs={'name': 'edit_permissions', 'value': 'edit_permissions'}).find_parent('form')

    data = {}
    user_field_name = None
    for hidden_field in default_permissions_form.find_all('input', {'type': 'hidden'}):
        data[hidden_field['name']] = hidden_field['value']
        if hidden_field['name'].endswith('user_id') and hidden_field['value'] == str(new_user_id):
            # the associated radio button is the first radio button in the same table row
            user_field_name = hidden_field.find_parent('tr').find('input', {'type': 'radio'})['name']
    for radio_button in default_permissions_form.find_all('input', {'type': 'radio'}):
        if radio_button.has_attr('checked') and not radio_button.has_attr('disabled'):
            data[radio_button['name']] = radio_button['value']
    assert user_field_name is not None
    assert data[user_field_name] == 'write'

    data[user_field_name] = 'read'
    data['edit_permissions'] = 'edit_permissions'
    assert session.post(flask_server.base_url + 'users/{}/preferences'.format(user.id), data=data).status_code == 200

    with flask_server.app.app_context():
        assert default_permissions.get_default_permissions_for_users(creator_id=user.id).get(new_user_id) == object_permissions.Permissions.READ


def test_edit_default_group_permissions(flask_server, user):
    with flask_server.app.app_context():
        group_id = groups.create_group("Example Group", "", user.id).id
        default_permissions.set_default_permissions_for_group(creator_id=user.id, group_id=group_id, permissions=object_permissions.Permissions.WRITE)
        assert default_permissions.get_default_permissions_for_groups(creator_id=user.id).get(group_id) == object_permissions.Permissions.WRITE

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/{}/preferences'.format(user.id))
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')

    default_permissions_form = document.find(attrs={'name': 'edit_permissions', 'value': 'edit_permissions'}).find_parent('form')

    data = {}
    group_field_name = None
    for hidden_field in default_permissions_form.find_all('input', {'type': 'hidden'}):
        data[hidden_field['name']] = hidden_field['value']
        if hidden_field['name'].endswith('group_id') and hidden_field['value'] == str(group_id):
            # the associated radio button is the first radio button in the same table row
            group_field_name = hidden_field.find_parent('tr').find('input', {'type': 'radio'})['name']
    for radio_button in default_permissions_form.find_all('input', {'type': 'radio'}):
        if radio_button.has_attr('checked') and not radio_button.has_attr('disabled'):
            data[radio_button['name']] = radio_button['value']
    assert group_field_name is not None
    assert data[group_field_name] == 'write'

    data[group_field_name] = 'read'
    data['edit_permissions'] = 'edit_permissions'
    assert session.post(flask_server.base_url + 'users/{}/preferences'.format(user.id), data=data).status_code == 200

    with flask_server.app.app_context():
        assert default_permissions.get_default_permissions_for_groups(creator_id=user.id).get(group_id) == object_permissions.Permissions.READ


def test_edit_default_project_permissions(flask_server, user):
    with flask_server.app.app_context():
        project_id = projects.create_project("Example Project", "", user.id).id
        default_permissions.set_default_permissions_for_project(creator_id=user.id, project_id=project_id, permissions=object_permissions.Permissions.WRITE)
        assert default_permissions.get_default_permissions_for_projects(creator_id=user.id).get(project_id) == object_permissions.Permissions.WRITE

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/{}/preferences'.format(user.id))
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')

    default_permissions_form = document.find(attrs={'name': 'edit_permissions', 'value': 'edit_permissions'}).find_parent('form')

    data = {}
    project_field_name = None
    for hidden_field in default_permissions_form.find_all('input', {'type': 'hidden'}):
        data[hidden_field['name']] = hidden_field['value']
        if hidden_field['name'].endswith('project_id') and hidden_field['value'] == str(project_id):
            # the associated radio button is the first radio button in the same table row
            project_field_name = hidden_field.find_parent('tr').find('input', {'type': 'radio'})['name']
    for radio_button in default_permissions_form.find_all('input', {'type': 'radio'}):
        if radio_button.has_attr('checked') and not radio_button.has_attr('disabled'):
            data[radio_button['name']] = radio_button['value']
    assert project_field_name is not None
    assert data[project_field_name] == 'write'

    data[project_field_name] = 'read'
    data['edit_permissions'] = 'edit_permissions'
    assert session.post(flask_server.base_url + 'users/{}/preferences'.format(user.id), data=data).status_code == 200

    with flask_server.app.app_context():
        assert default_permissions.get_default_permissions_for_projects(creator_id=user.id).get(project_id) == object_permissions.Permissions.READ


def test_add_default_user_permissions(flask_server, user):
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name="New User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/{}/preferences'.format(user.id))
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')

    default_permissions_form = document.find(attrs={'name': 'add_user_permissions', 'value': 'add_user_permissions'}).find_parent('form')

    data = {}
    for hidden_field in default_permissions_form.find_all('input', {'type': 'hidden'}):
        data[hidden_field['name']] = hidden_field['value']

    data['user_id'] = str(new_user_id)
    data['permissions'] = 'read'
    data['add_user_permissions'] = 'add_user_permissions'
    assert session.post(flask_server.base_url + 'users/{}/preferences'.format(user.id), data=data).status_code == 200

    with flask_server.app.app_context():
        assert default_permissions.get_default_permissions_for_users(creator_id=user.id).get(new_user_id) == object_permissions.Permissions.READ


def test_add_default_group_permissions(flask_server, user):
    with flask_server.app.app_context():
        group_id = groups.create_group("Example Group", "", user.id).id

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/{}/preferences'.format(user.id))
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')

    default_permissions_form = document.find(attrs={'name': 'add_group_permissions', 'value': 'add_group_permissions'}).find_parent('form')

    data = {}
    for hidden_field in default_permissions_form.find_all('input', {'type': 'hidden'}):
        data[hidden_field['name']] = hidden_field['value']

    data['group_id'] = str(group_id)
    data['permissions'] = 'read'
    data['add_group_permissions'] = 'add_group_permissions'
    assert session.post(flask_server.base_url + 'users/{}/preferences'.format(user.id), data=data).status_code == 200

    with flask_server.app.app_context():
        assert default_permissions.get_default_permissions_for_groups(creator_id=user.id).get(group_id) == object_permissions.Permissions.READ


def test_add_default_project_permissions(flask_server, user):
    with flask_server.app.app_context():
        project_id = projects.create_project("Example Project", "", user.id).id

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/{}/preferences'.format(user.id))
    assert r.status_code == 200

    document = BeautifulSoup(r.content, 'html.parser')

    default_permissions_form = document.find(attrs={'name': 'add_project_permissions', 'value': 'add_project_permissions'}).find_parent('form')

    data = {}
    for hidden_field in default_permissions_form.find_all('input', {'type': 'hidden'}):
        data[hidden_field['name']] = hidden_field['value']

    data['project_id'] = str(project_id)
    data['permissions'] = 'read'
    data['add_project_permissions'] = 'add_project_permissions'
    assert session.post(flask_server.base_url + 'users/{}/preferences'.format(user.id), data=data).status_code == 200

    with flask_server.app.app_context():
        assert default_permissions.get_default_permissions_for_projects(creator_id=user.id).get(project_id) == object_permissions.Permissions.READ


def test_user_preferences_change_password(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/users/')
    assert r.headers['Location'].endswith('/preferences')
    url = flask_server.base_url + r.headers['Location'][1:]
    r = session.get(url, allow_redirects=False)
    assert r.status_code == 200

    with flask_server.app.app_context():
        user = sampledb.models.users.User.query.filter_by(email="example@example.com").one()

    assert user.name == "Basic User"

    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200

    #  change password with typo in confirmation
    r = session.post(url, {
        'id': str(sampledb.models.Authentication.query.first().id),
        'password': 'xxxx',
        'password_confirmation': 'xyxx',
        'csrf_token': csrf_token,
        'edit': 'Edit'
    })
    assert r.status_code == 200
    assert 'Please enter the same password as above.' in r.text

    #  change password
    r = session.post(url, {
        'id': str(sampledb.models.Authentication.query.first().id),
        'password': 'xxxx',
        'password_confirmation': 'xxxx',
        'csrf_token': csrf_token,
        'edit': 'Edit'
    })
    assert r.status_code == 200
    assert 'Please enter the same password as above.' not in r.text

    # Create new session
    session = requests.session()

    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    # initially, the a link to the sign in page will be displayed
    r = session.get(flask_server.base_url)
    assert r.status_code == 200
    assert '/users/me/sign_in' in r.content.decode('utf-8')
    # Try to login
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    # it also contains a hidden CSRF token
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': 'example@example.com',
        'password': 'xxxx',
        'remember_me': False,
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # expect True, used new password
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True


def test_create_api_token_selenium(flask_server, driver, user):
    api_tokens = sampledb.logic.authentication.get_api_tokens(user.id)
    assert not api_tokens
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')
    driver.find_element(By.CSS_SELECTOR, '[data-target="#createApiTokenModal"]').click()

    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#createApiTokenModal #input-description')))
    driver.find_element(By.CSS_SELECTOR, '#createApiTokenModal #input-description').send_keys('Example API Token', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[name="create_api_token"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#viewApiTokenModal input[type="text"].disabled')))
    api_token = driver.find_element(By.CSS_SELECTOR, '#viewApiTokenModal input[type="text"].disabled').get_attribute("value")
    api_tokens = sampledb.logic.authentication.get_api_tokens(user.id)
    assert len(api_tokens) == 1
    assert api_tokens[0].login['description'] == 'Example API Token'
    assert api_tokens[0].login['login'] == api_token[:8]

    rows = driver.find_elements(By.CSS_SELECTOR, "#api_tokens + div tbody tr")
    assert len(rows) == 1
    assert rows[0].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'Example API Token'
    assert rows[0].find_element(By.CSS_SELECTOR, "td a").get_attribute("href") == flask_server.base_url + f'users/me/api_token_id/{api_tokens[0].id}/log/'


def test_view_api_tokens_selenium(flask_server, driver, user):
    api_token = secrets.token_hex(32)
    sampledb.logic.authentication.add_api_token(user.id, api_token, 'Example API Token')
    sampledb.logic.authentication.add_api_token(user.id, api_token, 'Other API Token')

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    rows = driver.find_elements(By.CSS_SELECTOR, "#api_tokens + div tbody tr")
    assert len(rows) == 2
    assert rows[0].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'Example API Token'
    assert rows[1].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'Other API Token'


def test_delete_api_token_selenium(flask_server, driver, user):
    api_token = secrets.token_hex(32)
    sampledb.logic.authentication.add_api_token(user.id, api_token, 'Example API Token')
    sampledb.logic.authentication.add_api_token(user.id, api_token, 'Other API Token')

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    rows = driver.find_elements(By.CSS_SELECTOR, "#api_tokens + div tbody tr")
    assert len(rows) == 2
    assert rows[0].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'Example API Token'
    with wait_for_page_load(driver):
        rows[0].find_element(By.CSS_SELECTOR, "td button").click()

    rows = driver.find_elements(By.CSS_SELECTOR, "#api_tokens + div tbody tr")
    assert len(rows) == 1
    assert rows[0].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'Other API Token'
    assert len(sampledb.logic.authentication.get_api_tokens(user.id)) == 1
    assert sampledb.logic.authentication.get_api_tokens(user.id)[0].login['description'] == 'Other API Token'


def test_user_add_email_authentication_method_selenium(flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    assert {
        authentication_method.login['login']: authentication_method.confirmed
        for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
        'example@example.com': True
    }

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addAuthenticationMethodModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-login')))
    assert driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodTypeSelect + button').text == 'Email'
    driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-login').send_keys('user@example.com', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-password').send_keys('password', Keys.TAB)
    with sampledb.mail.record_messages() as outbox:
        with wait_for_page_load(driver):
            driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal button[type="submit"]').click()
        WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#authentication_methods + div tbody tr:nth-child(2)')))

    # check if the authentication method got added
    assert {
        authentication_method.login['login']: authentication_method.confirmed
        for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
        'example@example.com': True,
        'user@example.com': False
    }

    # check if a confirmation mail was sent
    assert len(outbox) == 1
    assert 'user@example.com' in outbox[0].recipients
    message = outbox[0].html
    assert 'SampleDB Email Confirmation' in message

    # open confirmation link
    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[2].split('"')[0]
    driver.get(confirmation_url)

    # check if the authentication method got confirmed
    assert {
       authentication_method.login['login']: authentication_method.confirmed
       for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
   } == {
       'example@example.com': True,
       'user@example.com': True
   }


def test_user_add_email_authentication_method_already_exists_selenium(flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    add_email_authentication(user_id=user.id, email='user@example.com', password='password', confirmed=True)
    assert {
        authentication_method.login['login']: authentication_method.confirmed
        for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
        'example@example.com': True,
        'user@example.com': True
    }

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addAuthenticationMethodModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-login')))
    assert driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodTypeSelect + button').text == 'Email'
    driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-login').send_keys('user@example.com', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-password').send_keys('password', Keys.TAB)
    with sampledb.mail.record_messages() as outbox:
        with wait_for_page_load(driver):
            driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal button[type="submit"]').click()
    assert len(outbox) == 0
    assert 'Failed to add an authentication method.' in driver.find_element(By.CSS_SELECTOR, '.alert-danger').get_attribute('innerText')

    assert {
       authentication_method.login['login']: authentication_method.confirmed
       for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
   } == {
       'example@example.com': True,
       'user@example.com': True
   }


def test_user_add_email_authentication_method_empty_email_selenium(flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    assert {
        authentication_method.login['login']: authentication_method.confirmed
        for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
        'example@example.com': True
    }

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addAuthenticationMethodModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-login')))
    assert driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodTypeSelect + button').text == 'Email'
    driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-login').send_keys('', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal #input-password').send_keys('password', Keys.TAB)
    with sampledb.mail.record_messages() as outbox:
        with wait_for_page_load(driver):
            driver.find_element(By.CSS_SELECTOR, '#addAuthenticationMethodModal button[type="submit"]').click()
    assert len(outbox) == 0
    assert 'Failed to add an authentication method.' in driver.find_element(By.CSS_SELECTOR, '.alert-danger').get_attribute('innerText')

    assert {
       authentication_method.login['login']: authentication_method.confirmed
       for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
   } == {
       'example@example.com': True
   }


def test_user_preferences_change_password_selenium(flask_server, driver, user):
    authentication_method = sampledb.models.Authentication.query.first()
    assert sampledb.logic.authentication._validate_password_authentication(authentication_method, 'abc.123')

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    driver.find_element(By.CSS_SELECTOR, f'[data-target="#pwModal{authentication_method.id}"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, f'#pwModal{authentication_method.id} #input-pw')))
    driver.find_element(By.CSS_SELECTOR, f'#pwModal{authentication_method.id} #input-pw').send_keys('password', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, f'#pwModal{authentication_method.id} #input-pw-confirmation').send_keys('password', Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, f'#pwModal{authentication_method.id} button[type="submit"][name="edit"]').click()

    sampledb.db.session.refresh(authentication_method)
    assert sampledb.logic.authentication._validate_password_authentication(authentication_method, 'password')


def test_user_preferences_change_password_too_short_selenium(flask_server, driver, user):
    authentication_method = sampledb.models.Authentication.query.first()
    assert sampledb.logic.authentication._validate_password_authentication(authentication_method, 'abc.123')

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    driver.find_element(By.CSS_SELECTOR, f'[data-target="#pwModal{authentication_method.id}"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, f'#pwModal{authentication_method.id} #input-pw')))
    driver.find_element(By.CSS_SELECTOR, f'#pwModal{authentication_method.id} #input-pw').send_keys('pw', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, f'#pwModal{authentication_method.id} #input-pw-confirmation').send_keys('pw', Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, f'#pwModal{authentication_method.id} button[type="submit"][name="edit"]').click()

    sampledb.db.session.refresh(authentication_method)
    assert sampledb.logic.authentication._validate_password_authentication(authentication_method, 'abc.123')
    assert "Failed to change password." in driver.find_element(By.CSS_SELECTOR, ".alert-danger").get_attribute("innerText")


def test_user_remove_authentication_method_selenium(flask_server, driver, user):
    add_email_authentication(user_id=user.id, email='user@example.com', password='password', confirmed=True)
    assert {
           authentication_method.login['login']
           for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
       'example@example.com', 'user@example.com'
    }

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    rows = driver.find_elements(By.CSS_SELECTOR, "#authentication_methods + div tbody tr")
    assert len(rows) == 2
    assert rows[0].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'example@example.com'
    assert rows[0].find_element(By.CSS_SELECTOR, 'td button[name="remove"]').get_attribute('disabled') is None
    assert rows[1].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'user@example.com'
    assert rows[1].find_element(By.CSS_SELECTOR, 'td button[name="remove"]').get_attribute('disabled') is None
    with wait_for_page_load(driver):
        rows[1].find_element(By.CSS_SELECTOR, 'td button[name="remove"]').click()

    assert {
           authentication_method.login['login']
           for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
       'example@example.com',
    }

    rows = driver.find_elements(By.CSS_SELECTOR, "#authentication_methods + div tbody tr")
    assert len(rows) == 1
    assert rows[0].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'example@example.com'
    assert rows[0].find_element(By.CSS_SELECTOR, 'td button[name="remove"]').get_attribute('disabled') is not None

def test_user_remove_authentication_method_already_removed_selenium(flask_server, driver, user):
    add_email_authentication(user_id=user.id, email='user@example.com', password='password', confirmed=True)
    assert {
           authentication_method.login['login']
           for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
       'example@example.com', 'user@example.com'
    }

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    authentication_method = sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).filter(sampledb.models.Authentication.login['login'].astext == 'example@example.com').first()
    sampledb.logic.authentication.remove_authentication_method(authentication_method.id)
    assert {
           authentication_method.login['login']
           for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
       'user@example.com',
    }

    rows = driver.find_elements(By.CSS_SELECTOR, "#authentication_methods + div tbody tr")
    assert len(rows) == 2
    assert rows[0].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'example@example.com'
    assert rows[0].find_element(By.CSS_SELECTOR, 'td button[name="remove"]').get_attribute('disabled') is None
    assert rows[1].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'user@example.com'
    assert rows[1].find_element(By.CSS_SELECTOR, 'td button[name="remove"]').get_attribute('disabled') is None
    with wait_for_page_load(driver):
        rows[1].find_element(By.CSS_SELECTOR, 'td button[name="remove"]').click()

    assert {
           authentication_method.login['login']
           for authentication_method in sampledb.models.Authentication.query.filter_by(user_id=user.id, type=sampledb.models.AuthenticationType.EMAIL).all()
    } == {
       'user@example.com',
    }

    rows = driver.find_elements(By.CSS_SELECTOR, "#authentication_methods + div tbody tr")
    assert len(rows) == 1
    assert rows[0].find_element(By.CSS_SELECTOR, "td:first-child").get_attribute("innerText") == 'user@example.com'
    assert rows[0].find_element(By.CSS_SELECTOR, 'td button[name="remove"]').get_attribute('disabled') is not None


def test_user_preferences_change_name_selenium(flask_server, driver, user):
    assert user.name == 'Basic User'
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    driver.find_element(By.CSS_SELECTOR, '#input-username').clear()
    driver.find_element(By.CSS_SELECTOR, '#input-username').send_keys('Renamed User', Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, 'button[name="change"]').click()

    assert driver.find_element(By.CSS_SELECTOR, '#input-username').get_attribute('value') == 'Renamed User'
    user = sampledb.logic.users.get_user(user.id)
    assert user.name == 'Renamed User'


def test_user_preferences_change_email_selenium(flask_server, driver, user):
    assert user.email == 'example@example.com'
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_element(By.CSS_SELECTOR, '#input-email').get_attribute('value') == 'example@example.com'

    driver.find_element(By.CSS_SELECTOR, '#input-email').clear()
    driver.find_element(By.CSS_SELECTOR, '#input-email').send_keys('user@example.com', Keys.TAB)
    with sampledb.mail.record_messages() as outbox:
        with wait_for_page_load(driver):
            driver.find_element(By.CSS_SELECTOR, 'button[name="change"]').click()

    assert driver.find_element(By.CSS_SELECTOR, '#input-email').get_attribute('value') == 'example@example.com'
    user = sampledb.logic.users.get_user(user.id)
    assert user.email == 'example@example.com'

    # check if a confirmation mail was sent
    assert len(outbox) == 1
    assert 'user@example.com' in outbox[0].recipients
    message = outbox[0].html
    assert 'SampleDB Email Confirmation' in message

    # open the confirmation link
    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[2].split('"')[0]
    driver.get(confirmation_url)

    # check that the email was updated after confirming it
    assert driver.find_element(By.CSS_SELECTOR, '#input-email').get_attribute('value') == 'user@example.com'
    user = sampledb.logic.users.get_user(user.id)
    assert user.email == 'user@example.com'


def test_user_preferences_change_orcid_id_selenium(flask_server, driver, user):
    assert user.orcid is None
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    driver.find_element(By.CSS_SELECTOR, '#input-orcid').clear()
    driver.find_element(By.CSS_SELECTOR, '#input-orcid').send_keys('0000-0002-1825-0097', Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, 'button[name="change"]').click()

    assert driver.find_element(By.CSS_SELECTOR, '#input-orcid').get_attribute('value') == '0000-0002-1825-0097'
    user = sampledb.logic.users.get_user(user.id)
    assert user.orcid == '0000-0002-1825-0097'


def test_user_preferences_change_affiliation_selenium(flask_server, driver, user):
    assert user.affiliation is None
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    driver.find_element(By.CSS_SELECTOR, '#input-affiliation').clear()
    driver.find_element(By.CSS_SELECTOR, '#input-affiliation').send_keys('Example University', Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, 'button[name="change"]').click()

    assert driver.find_element(By.CSS_SELECTOR, '#input-affiliation').get_attribute('value') == 'Example University'
    user = sampledb.logic.users.get_user(user.id)
    assert user.affiliation == 'Example University'


def test_user_preferences_change_role_selenium(flask_server, driver, user):
    assert user.role is None
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    driver.find_element(By.CSS_SELECTOR, '#input-role').clear()
    driver.find_element(By.CSS_SELECTOR, '#input-role').send_keys('Example User', Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, 'button[name="change"]').click()

    assert driver.find_element(By.CSS_SELECTOR, '#input-role').get_attribute('value') == 'Example User'
    user = sampledb.logic.users.get_user(user.id)
    assert user.role == 'Example User'


def test_user_preferences_change_extra_field_selenium(flask_server, driver, user):
    flask.current_app.config['EXTRA_USER_FIELDS'] = {
        'location': {'en': 'Location'}
    }
    assert user.extra_fields == {}
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    driver.find_element(By.CSS_SELECTOR, '#extra_field_location').clear()
    driver.find_element(By.CSS_SELECTOR, '#extra_field_location').send_keys('Building A, Room 1', Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, 'button[name="change"]').click()

    assert driver.find_element(By.CSS_SELECTOR, '#extra_field_location').get_attribute('value') == 'Building A, Room 1'
    user = sampledb.logic.users.get_user(user.id)
    assert user.extra_fields == {
        'location': 'Building A, Room 1'
    }


def test_user_preferences_change_notification_modes_selenium(flask_server, driver, user):
    # create an instrument to be able to test the instrument scientist notification types
    instrument = sampledb.logic.instruments.create_instrument()
    sampledb.logic.instruments.add_instrument_responsible_user(instrument.id, user.id)

    for notification_type in sampledb.logic.notifications.NotificationType:
        assert sampledb.logic.notifications.get_notification_modes(user.id).get(notification_type, sampledb.logic.notifications.NotificationMode.WEBAPP) == sampledb.logic.notifications.NotificationMode.WEBAPP

        driver.get(flask_server.base_url + f'users/{user.id}/autologin')
        driver.get(flask_server.base_url + 'users/me/preferences')

        assert len(driver.find_elements(By.CSS_SELECTOR, f'[name="notification_mode_for_type_{notification_type.name.lower()}"]')) >= 2
        assert all(element.get_attribute("id") in (f'notification_mode_for_type_{notification_type.name.lower()}_webapp', f'notification_mode_for_type_{notification_type.name.lower()}_ignore', f'notification_mode_for_type_{notification_type.name.lower()}_email') for element in driver.find_elements(By.CSS_SELECTOR, f'[name="notification_mode_for_type_{notification_type.name.lower()}"]'))

        assert driver.find_element(By.CSS_SELECTOR, f'[name="notification_mode_for_type_{notification_type.name.lower()}"]:checked').get_attribute('id') == f'notification_mode_for_type_{notification_type.name.lower()}_webapp'
        driver.find_element(By.CSS_SELECTOR, f'#notification_mode_for_type_{notification_type.name.lower()}_email').click()
        with wait_for_page_load(driver):
            driver.find_element(By.CSS_SELECTOR, 'button[name="edit_notification_settings"]').click()

        assert driver.find_element(By.CSS_SELECTOR, f'[name="notification_mode_for_type_{notification_type.name.lower()}"]:checked').get_attribute('id') == f'notification_mode_for_type_{notification_type.name.lower()}_email'
        user = sampledb.logic.users.get_user(user.id)
        assert sampledb.logic.notifications.get_notification_modes(user.id)[notification_type] == sampledb.logic.notifications.NotificationMode.EMAIL

@pytest.mark.parametrize(
    [
        'setting_name', 'radio_button_name', 'input_value_before', 'input_value_after', 'setting_value_before', 'setting_value_after'
    ], [
        ('USE_SCHEMA_EDITOR', 'input-use-schema-editor', 'yes', 'no', True, False),
        ('USE_SCHEMA_EDITOR', 'input-use-schema-editor', 'no', 'yes', False, True),
        ('SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE', 'input-show-object-type-and-id-on-object-page', 'default', 'no', None, False),
        ('SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE', 'input-show-object-type-and-id-on-object-page', 'default', 'yes', None, True),
        ('SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE', 'input-show-object-type-and-id-on-object-page', 'yes', 'default', True, None),
        ('SHOW_OBJECT_TITLE', 'input-show-object-title', 'default', 'no', None, False),
        ('SHOW_OBJECT_TITLE', 'input-show-object-title', 'default', 'yes', None, True),
        ('SHOW_OBJECT_TITLE', 'input-show-object-title', 'yes', 'default', True, None),
        ('FULL_WIDTH_OBJECTS_TABLE', 'input-full-width-objects-table', 'default', 'no', None, False),
        ('FULL_WIDTH_OBJECTS_TABLE', 'input-full-width-objects-table', 'default', 'yes', None, True),
        ('FULL_WIDTH_OBJECTS_TABLE', 'input-full-width-objects-table', 'yes', 'default', True, None),
    ]
)
def test_change_other_settings_radio_buttons_selenium(flask_server, driver, user, setting_name, radio_button_name, input_value_before, input_value_after, setting_value_before, setting_value_after):
    sampledb.logic.settings.set_user_settings(user.id, {setting_name: setting_value_before})
    assert sampledb.logic.settings.get_user_setting(user.id, setting_name) == setting_value_before

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    assert driver.find_element(By.CSS_SELECTOR, f'[name="{radio_button_name}"][value="{input_value_before}"]').get_attribute("checked")
    assert not driver.find_element(By.CSS_SELECTOR, f'[name="{radio_button_name}"][value="{input_value_after}"]').get_attribute("checked")
    driver.find_element(By.CSS_SELECTOR, f'[name="{radio_button_name}"][value="{input_value_after}"]').click()
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="edit_other_settings"]').click()

    assert sampledb.logic.settings.get_user_setting(user.id, setting_name) == setting_value_after


@pytest.mark.parametrize(
    [
        'setting_name', 'select_name', 'input_value_before', 'input_value_after', 'setting_value_before', 'setting_value_after'
    ], [
        ('AUTO_TZ', 'select-timezone', 'auto_tz', 'Etc/UTC', True, False),
        ('AUTO_TZ', 'select-timezone', 'Etc/UTC', 'auto_tz', False, True),
        ('TIMEZONE', 'select-timezone', 'Etc/UTC', 'Europe/Berlin', 'Etc/UTC', 'Europe/Berlin'),
        ('OBJECTS_PER_PAGE', 'input-objects-per-page', 'all', '10', None, 10),
        ('OBJECTS_PER_PAGE', 'input-objects-per-page', '25', 'all', 25, None),
        ('AUTO_LC', 'select-locale', 'auto_lc', 'en', True, False),
        ('AUTO_LC', 'select-locale', 'en', 'auto_lc', False, True),
        ('LOCALE', 'select-locale', 'en', 'de', 'en', 'de'),
    ]
)
def test_change_other_settings_selectpicker_selenium(flask_server, driver, user, setting_name, select_name, input_value_before, input_value_after, setting_value_before, setting_value_after):
    if setting_name == 'AUTO_TZ':
        if setting_value_before:
            sampledb.logic.settings.set_user_settings(user.id, {'TIMEZONE': None})
        else:
            sampledb.logic.settings.set_user_settings(user.id, {'TIMEZONE': 'Etc/UTC'})
    if setting_name == 'TIMEZONE':
        if setting_value_before:
            sampledb.logic.settings.set_user_settings(user.id, {'AUTO_TZ': False})
        else:
            sampledb.logic.settings.set_user_settings(user.id, {'AUTO_TZ': True})
    if setting_name == 'AUTO_LC':
        if setting_value_before:
            sampledb.logic.settings.set_user_settings(user.id, {'LOCALE': None})
        else:
            sampledb.logic.settings.set_user_settings(user.id, {'LOCALE': 'en'})
    if setting_name == 'LOCALE':
        if setting_value_before:
            sampledb.logic.settings.set_user_settings(user.id, {'AUTO_LC': False})
        else:
            sampledb.logic.settings.set_user_settings(user.id, {'AUTO_LC': True})
    sampledb.logic.settings.set_user_settings(user.id, {setting_name: setting_value_before})
    assert sampledb.logic.settings.get_user_setting(user.id, setting_name) == setting_value_before

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    assert driver.find_element(By.CSS_SELECTOR, f'[name="{select_name}"] option[value="{input_value_before}"]').get_attribute("selected")
    assert driver.find_element(By.CSS_SELECTOR, f'[name="{select_name}"] option[value="{input_value_after}"]').get_attribute("selected") is None
    input_text_after = driver.find_element(By.CSS_SELECTOR, f'[name="{select_name}"] option[value="{input_value_after}"]').get_attribute("innerText")
    driver.find_element(By.CSS_SELECTOR, f'[data-id="{select_name}"]').click()
    driver.find_element(By.XPATH, f'//span[text()="{input_text_after}"]').click()
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="edit_other_settings"]').click()

    assert sampledb.logic.settings.get_user_setting(user.id, setting_name) == setting_value_after


def test_change_locale_notification_selenium(flask_server, driver, user):
    sampledb.logic.settings.set_user_settings(user.id, {'AUTO_LC': False})
    sampledb.logic.settings.set_user_settings(user.id, {'LOCALE': 'en'})

    assert sampledb.logic.settings.get_user_setting(user.id, 'LOCALE') == 'en'

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    input_text_after = driver.find_element(By.CSS_SELECTOR, '[name="select-locale"] option[value="de"]').get_attribute("innerText")
    driver.find_element(By.CSS_SELECTOR, '[data-id="select-locale"]').click()
    driver.find_element(By.XPATH, f'//span[text()="{input_text_after}"]').click()
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="edit_other_settings"]').click()

    assert sampledb.logic.settings.get_user_setting(user.id, 'LOCALE') == 'de'

    assert "Ihre Einstellungen wurden erfolgreich aktualisiert." in driver.find_element(By.CSS_SELECTOR, '.alert.alert-success').get_attribute("innerText")


@pytest.mark.parametrize(
    [
        'setting_name', 'radio_button_name', 'input_value_before', 'input_value_after', 'setting_value_before', 'setting_value_after'
    ], [
        ('USE_ADMIN_PERMISSIONS', 'input-use-admin-permissions', 'yes', 'no', True, False),
        ('USE_ADMIN_PERMISSIONS', 'input-use-admin-permissions', 'no', 'yes', False, True),
        ('SHOW_INVITATION_LOG', 'input-show-invitation-log', 'yes', 'no', True, False),
        ('SHOW_INVITATION_LOG', 'input-show-invitation-log', 'no', 'yes', False, True),
        ('SHOW_HIDDEN_USERS_AS_ADMIN', 'input-show-hidden-users-as-admin', 'yes', 'no', True, False),
        ('SHOW_HIDDEN_USERS_AS_ADMIN', 'input-show-hidden-users-as-admin', 'no', 'yes', False, True),
    ]
)
def test_change_admin_settings_radio_buttons_selenium(flask_server, driver, user, setting_name, radio_button_name, input_value_before, input_value_after, setting_value_before, setting_value_after):
    sampledb.logic.users.set_user_administrator(user.id, True)
    sampledb.logic.settings.set_user_settings(user.id, {setting_name: setting_value_before})
    assert sampledb.logic.settings.get_user_setting(user.id, setting_name) == setting_value_before

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    assert driver.find_elements(By.CSS_SELECTOR, f'[name="{radio_button_name}"]')
    assert driver.find_element(By.CSS_SELECTOR, f'[name="{radio_button_name}"][value="{input_value_before}"]').get_attribute("checked")
    assert not driver.find_element(By.CSS_SELECTOR, f'[name="{radio_button_name}"][value="{input_value_after}"]').get_attribute("checked")
    driver.find_element(By.CSS_SELECTOR, f'[name="{radio_button_name}"][value="{input_value_after}"]').click()
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="edit_other_settings"]').click()

    assert sampledb.logic.settings.get_user_setting(user.id, setting_name) == setting_value_after

    sampledb.logic.users.set_user_administrator(user.id, False)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert not driver.find_elements(By.CSS_SELECTOR, f'[name="{radio_button_name}"]')


def test_add_webhook_selenium(flask_server, driver, user):
    flask.current_app.config['WEBHOOKS_ALLOW_HTTP'] = True

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    sampledb.logic.users.set_user_administrator(user.id, True)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    sampledb.logic.users.set_user_administrator(user.id, False)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] = True
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 0

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addWebhookName')))
    driver.find_element(By.CSS_SELECTOR, '#addWebhookName').send_keys('Example Webhook', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget').send_keys(flask_server.base_url, Keys.TAB)
    assert not sampledb.logic.webhooks.get_webhooks(user_id=user.id)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="add_webhook"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#webhook-secret input')))
    assert len(sampledb.logic.webhooks.get_webhooks(user_id=user.id)) == 1
    webhook = sampledb.logic.webhooks.get_webhooks(user_id=user.id)[0]
    assert webhook.user_id == user.id
    assert webhook.target_url == flask_server.base_url
    assert webhook.secret == driver.find_element(By.CSS_SELECTOR, '#webhook-secret input').get_attribute("value")
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 1
    assert driver.find_element(By.CSS_SELECTOR, '#webhooks + div tbody tr td:first-child').get_attribute("innerText") == "Example Webhook"
    assert driver.find_element(By.CSS_SELECTOR, '#webhooks + div tbody tr td:nth-child(2)').get_attribute("innerText") == flask_server.base_url


def test_add_webhook_exist_already_selenium(flask_server, driver, user):
    flask.current_app.config['WEBHOOKS_ALLOW_HTTP'] = True
    sampledb.logic.webhooks.create_webhook(
        type=sampledb.models.WebhookType.OBJECT_LOG,
        user_id=user.id,
        target_url=flask_server.base_url,
        name='Example Webhook'
    )

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    sampledb.logic.users.set_user_administrator(user.id, True)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    sampledb.logic.users.set_user_administrator(user.id, False)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] = True
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 1

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addWebhookName')))
    driver.find_element(By.CSS_SELECTOR, '#addWebhookName').send_keys('Example Webhook', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget').send_keys(flask_server.base_url, Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="add_webhook"]').click()
    assert 'A webhook of this type with this target address already exists' in driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget + .help-block').get_attribute('innerText')
    assert len(sampledb.logic.webhooks.get_webhooks(user_id=user.id)) == 1


def test_add_webhook_http_selenium(flask_server, driver, user):
    flask.current_app.config['WEBHOOKS_ALLOW_HTTP'] = False

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    sampledb.logic.users.set_user_administrator(user.id, True)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    sampledb.logic.users.set_user_administrator(user.id, False)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] = True
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 0

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addWebhookName')))
    driver.find_element(By.CSS_SELECTOR, '#addWebhookName').send_keys('Example Webhook', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget').send_keys(flask_server.base_url, Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="add_webhook"]').click()
    assert 'Only secure communication via https is allowed' in driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget + .help-block').get_attribute('innerText')
    assert not sampledb.logic.webhooks.get_webhooks(user_id=user.id)


def test_add_webhook_invalid_url_selenium(flask_server, driver, user):
    flask.current_app.config['WEBHOOKS_ALLOW_HTTP'] = True

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    sampledb.logic.users.set_user_administrator(user.id, True)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    sampledb.logic.users.set_user_administrator(user.id, False)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] = True
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 0

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addWebhookName')))
    driver.find_element(By.CSS_SELECTOR, '#addWebhookName').send_keys('Example Webhook', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget').send_keys("example", Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="add_webhook"]').click()
    assert 'This webhook address is invalid' in driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget + .help-block').get_attribute('innerText')
    assert not sampledb.logic.webhooks.get_webhooks(user_id=user.id)


def test_add_webhook_admin_only_selenium(flask_server, driver, user):
    flask.current_app.config['WEBHOOKS_ALLOW_HTTP'] = True

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    sampledb.logic.users.set_user_administrator(user.id, True)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    sampledb.logic.users.set_user_administrator(user.id, False)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] = True
    driver.get(flask_server.base_url + 'users/me/preferences')
    flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] = False
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 0

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addWebhookName')))
    driver.find_element(By.CSS_SELECTOR, '#addWebhookName').send_keys('Example Webhook', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget').send_keys("example", Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="add_webhook"]').click()
    assert "You are not allowed to create Webhooks." in driver.find_element(By.CSS_SELECTOR, ".alert-danger").get_attribute("innerText")
    assert not sampledb.logic.webhooks.get_webhooks(user_id=user.id)


def test_add_webhook_blank_name_selenium(flask_server, driver, user):
    flask.current_app.config['WEBHOOKS_ALLOW_HTTP'] = True

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    sampledb.logic.users.set_user_administrator(user.id, True)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    sampledb.logic.users.set_user_administrator(user.id, False)
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')

    flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] = True
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert driver.find_elements(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]')
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 0

    driver.find_element(By.CSS_SELECTOR, '[data-target="#addWebhookModal"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#addWebhookName')))
    driver.find_element(By.CSS_SELECTOR, '#addWebhookName').send_keys('', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#addWebhookTarget').send_keys(flask_server.base_url, Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="add_webhook"]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, '#webhook-secret input')))
    assert len(sampledb.logic.webhooks.get_webhooks(user_id=user.id)) == 1
    webhook = sampledb.logic.webhooks.get_webhooks(user_id=user.id)[0]
    assert webhook.user_id == user.id
    assert webhook.target_url == flask_server.base_url
    assert webhook.secret == driver.find_element(By.CSS_SELECTOR, '#webhook-secret input').get_attribute("value")
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 1
    assert driver.find_element(By.CSS_SELECTOR, '#webhooks + div tbody tr td:first-child').get_attribute("innerText") == "—"
    assert driver.find_element(By.CSS_SELECTOR, '#webhooks + div tbody tr td:nth-child(2)').get_attribute("innerText") == flask_server.base_url


def test_remove_webhook_selenium(flask_server, driver, user):
    flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] = True

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 0

    sampledb.logic.webhooks.create_webhook(
        type=sampledb.models.WebhookType.OBJECT_LOG,
        user_id=user.id,
        target_url='https://example.com',
        name='Example Webhook',
    )

    driver.get(flask_server.base_url + 'users/me/preferences')
    assert len(driver.find_elements(By.CSS_SELECTOR, '#webhooks + div tbody tr')) == 1
    assert driver.find_element(By.CSS_SELECTOR, '#webhooks + div tbody tr td:first-child').get_attribute("innerText") == "Example Webhook"
    assert driver.find_element(By.CSS_SELECTOR, '#webhooks + div tbody tr td:nth-child(2)').get_attribute("innerText") == 'https://example.com'

    assert sampledb.logic.webhooks.get_webhooks(user_id=user.id)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '#webhooks + div tbody tr td:nth-child(4) button').click()
    assert not sampledb.logic.webhooks.get_webhooks(user_id=user.id)


def test_add_totp_two_factor_authentication_selenium(flask_server, driver, user):

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    driver.find_element(By.XPATH, '//a[text()="Set up TOTP-based Two-Factor Authentication"]').click()
    secret = driver.find_element(By.CSS_SELECTOR, "#totp_secret").get_attribute("innerText")
    for _ in range(2):
        form = driver.find_element(By.CSS_SELECTOR, '#main .container form')
        form.find_element(By.CSS_SELECTOR, 'input[name="code"]').send_keys(pyotp.TOTP(secret).now(), Keys.TAB)
        with wait_for_page_load(driver):
            form.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()
        if len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=True)) == 1:
            break
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=True)) == 1
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=False)) == 0


def test_disable_totp_two_factor_authentication_selenium(flask_server, driver, user):
    secret = pyotp.random_base32()
    method = sampledb.logic.authentication.create_totp_two_factor_authentication_method(user.id, secret, "Example TOTP")
    sampledb.logic.authentication.activate_two_factor_authentication_method(method.id)

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    rows = driver.find_elements(By.CSS_SELECTOR, 'h3[id="2fa"] + table tbody tr')
    assert len(rows) == 1
    assert rows[0].find_element(By.CSS_SELECTOR, 'td:first-child').get_attribute("innerText") == "Example TOTP"
    assert not rows[0].find_elements(By.CSS_SELECTOR, 'button[value="enable"]')
    assert rows[0].find_element(By.CSS_SELECTOR, 'button[value="delete"]').get_attribute("disabled")
    with wait_for_page_load(driver):
        rows[0].find_element(By.CSS_SELECTOR, 'button[value="disable"]').click()
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=True)) == 1
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=False)) == 0

    for _ in range(2):
        form = driver.find_element(By.CSS_SELECTOR, '#main .container form')
        form.find_element(By.CSS_SELECTOR, 'input[name="code"]').send_keys(pyotp.TOTP(secret).now(), Keys.TAB)
        with wait_for_page_load(driver):
            form.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()
        # the form might have failed if the code expired in just the wrong moment
        if len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=True)) == 0:
            break
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=True)) == 0
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=False)) == 1


def test_enable_totp_two_factor_authentication_selenium(flask_server, driver, user):
    secret = pyotp.random_base32()
    sampledb.logic.authentication.create_totp_two_factor_authentication_method(user.id, secret, "Example TOTP")

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    rows = driver.find_elements(By.CSS_SELECTOR, 'h3[id="2fa"] + table tbody tr')
    assert len(rows) == 1
    assert rows[0].find_element(By.CSS_SELECTOR, 'td:first-child').get_attribute("innerText") == "Example TOTP"
    assert not rows[0].find_elements(By.CSS_SELECTOR, 'button[value="disable"]')
    with wait_for_page_load(driver):
        rows[0].find_element(By.CSS_SELECTOR, 'button[value="enable"]').click()
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=True)) == 0
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=False)) == 1

    for _ in range(2):
        form = driver.find_element(By.CSS_SELECTOR, '#main .container form')
        form.find_element(By.CSS_SELECTOR, 'input[name="code"]').send_keys(pyotp.TOTP(secret).now(), Keys.TAB)
        with wait_for_page_load(driver):
            form.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()
        # the form might have failed if the code expired in just the wrong moment
        if len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=True)) == 1:
            break
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=True)) == 1
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id, active=False)) == 0


def test_delete_totp_two_factor_authentication_selenium(flask_server, driver, user):
    secret = pyotp.random_base32()
    sampledb.logic.authentication.create_totp_two_factor_authentication_method(user.id, secret, "Example TOTP")

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    rows = driver.find_elements(By.CSS_SELECTOR, 'h3[id="2fa"] + table tbody tr')
    assert len(rows) == 1
    assert rows[0].find_element(By.CSS_SELECTOR, 'td:first-child').get_attribute("innerText") == "Example TOTP"
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id)) == 1
    with wait_for_page_load(driver):
        rows[0].find_element(By.CSS_SELECTOR, 'button[value="delete"]').click()
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id)) == 0


def test_delete_active_totp_two_factor_authentication_selenium(flask_server, driver, user):
    secret = pyotp.random_base32()
    method = sampledb.logic.authentication.create_totp_two_factor_authentication_method(user.id, secret, "Example TOTP")

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    rows = driver.find_elements(By.CSS_SELECTOR, 'h3[id="2fa"] + table tbody tr')
    assert len(rows) == 1
    assert rows[0].find_element(By.CSS_SELECTOR, 'td:first-child').get_attribute("innerText") == "Example TOTP"
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id)) == 1

    sampledb.logic.authentication.activate_two_factor_authentication_method(method.id)
    with wait_for_page_load(driver):
        rows[0].find_element(By.CSS_SELECTOR, 'button[value="delete"]').click()
    assert len(sampledb.logic.authentication.get_two_factor_authentication_methods(user_id=user.id)) == 1
    assert "You cannot delete an active two-factor authentication method." in driver.find_element(By.CSS_SELECTOR, ".alert-danger").get_attribute("innerText")


def test_reset_email_password_selenium(flask_server, driver, user):
    authentication_method = sampledb.models.Authentication.query.first()
    assert sampledb.logic.authentication._validate_password_authentication(authentication_method, 'abc.123')

    driver.get(flask_server.base_url + 'users/me/preferences')
    driver.find_element(By.CSS_SELECTOR, '#input-email').send_keys("example@example.com", Keys.TAB)
    with sampledb.mail.record_messages() as outbox:
        with wait_for_page_load(driver):
            driver.find_element(By.XPATH, f'//button[text()="Send Recovery Email"]').click()

    # check if a recovery mail was sent
    assert len(outbox) == 1
    assert 'example@example.com' in outbox[0].recipients
    message = outbox[0].html
    assert 'SampleDB Account Recovery' in message

    recovery_url = flask_server.base_url + message.split(flask_server.base_url)[2].split('"')[0]
    driver.get(recovery_url)
    driver.find_element(By.CSS_SELECTOR, "#form-password-recovery #input-password").send_keys('password', Keys.TAB)
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '#form-password-recovery button[type="submit"]').click()

    sampledb.db.session.refresh(authentication_method)
    assert sampledb.logic.authentication._validate_password_authentication(authentication_method, 'password')

def test_delete_dataverse_api_token_selenium(flask_server, driver, user):
    sampledb.logic.settings.set_user_settings(user.id, {
        'DATAVERSE_API_TOKEN': 'api_token'
    })

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'users/me/preferences')

    assert sampledb.logic.settings.get_user_setting(user.id, 'DATAVERSE_API_TOKEN') == 'api_token'
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, '[name="delete_dataverse_api_token"]').click()
    assert not sampledb.logic.settings.get_user_setting(user.id, 'DATAVERSE_API_TOKEN')


def test_user_preferences_wrong_user_selenium(flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'users/{user.id + 1}/preferences')
    assert driver.find_elements(By.XPATH, '//h1[contains(text(), "403")]')


def test_user_preferences_login_not_fresh_selenium(flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin?fresh=false')
    driver.get(flask_server.base_url + f'users/{user.id}/preferences')
    assert driver.find_elements(By.XPATH, '//h1[contains(text(), "Sign in to")]')
    assert driver.find_elements(By.XPATH, '//div[contains(text(), "please sign in again")]')


def test_user_preferences_login_not_authorized_selenium(flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/preferences')
    assert driver.find_elements(By.XPATH, '//h1[contains(text(), "Sign in to")]')
    assert not driver.find_elements(By.XPATH, '//div[contains(text(), "please sign in again")]')


def test_add_user_to_default_permissions_selenium(flask_server, driver, user):
    other_users = [
        sampledb.logic.users.create_user(
            name="Other User",
            email="other@example.com",
            type=sampledb.models.UserType.PERSON
        )
        for _ in range(3)
    ]
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'users/{user.id}/preferences')
    assert sampledb.logic.default_permissions.get_default_permissions_for_users(user.id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    add_user_form = driver.find_element(By.CSS_SELECTOR, "#add_user + form")
    add_user_form.find_element(By.CSS_SELECTOR, '.dropdown-toggle').click()
    add_user_form.find_element(By.XPATH, f'//span[contains(text(), "(#{other_users[1].id})")]').click()
    add_user_form.find_element(By.CSS_SELECTOR, 'input[type="radio"][name="permissions"][value="write"]').click()
    with wait_for_page_load(driver):
        add_user_form.find_element(By.CSS_SELECTOR, '[name="add_user_permissions"]').click()
    assert sampledb.logic.default_permissions.get_default_permissions_for_users(user.id) == {
        user.id: sampledb.models.Permissions.GRANT,
        other_users[1].id: sampledb.models.Permissions.WRITE
    }


def test_add_basic_group_to_default_permissions_selenium(flask_server, driver, user):
    basic_groups = [
        sampledb.logic.groups.create_group(
            name=f"Basic Group {i}",
            description="",
            initial_user_id=user.id
        )
        for i in range(3)
    ]
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'users/{user.id}/preferences')
    assert sampledb.logic.default_permissions.get_default_permissions_for_groups(user.id) == {}

    add_group_form = driver.find_element(By.XPATH, '//h3[contains(text(), "Add Basic Group")]/following-sibling::form')
    add_group_form.find_element(By.CSS_SELECTOR, '.dropdown-toggle').click()
    add_group_form.find_element(By.XPATH, f'//span[contains(text(), "Basic Group 1")]').click()
    add_group_form.find_element(By.CSS_SELECTOR, 'input[type="radio"][name="permissions"][value="grant"]').click()
    with wait_for_page_load(driver):
        add_group_form.find_element(By.CSS_SELECTOR, '[name="add_group_permissions"]').click()
    assert sampledb.logic.default_permissions.get_default_permissions_for_groups(user.id) == {
        basic_groups[1].id: sampledb.models.Permissions.GRANT
    }


def test_add_project_group_to_default_permissions_selenium(flask_server, driver, user):
    project_groups = [
        sampledb.logic.projects.create_project(
            name=f"Project Group {i}",
            description="",
            initial_user_id=user.id
        )
        for i in range(3)
    ]
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'users/{user.id}/preferences')
    assert sampledb.logic.default_permissions.get_default_permissions_for_projects(user.id) == {}

    add_group_form = driver.find_element(By.XPATH, '//h3[contains(text(), "Add Project Group")]/following-sibling::form')
    add_group_form.find_element(By.CSS_SELECTOR, '.dropdown-toggle').click()
    add_group_form.find_element(By.XPATH, f'//span[contains(text(), "Project Group 1")]').click()
    add_group_form.find_element(By.CSS_SELECTOR, 'input[type="radio"][name="permissions"][value="grant"]').click()
    with wait_for_page_load(driver):
        add_group_form.find_element(By.CSS_SELECTOR, '[name="add_project_permissions"]').click()
    assert sampledb.logic.default_permissions.get_default_permissions_for_projects(user.id) == {
        project_groups[1].id: sampledb.models.Permissions.GRANT
    }


def test_edit_default_permissions_selenium(flask_server, driver, user):
    other_users = [
        sampledb.logic.users.create_user(
            name="Other User",
            email="other@example.com",
            type=sampledb.models.UserType.PERSON
        )
        for _ in range(4)
    ]
    basic_groups = [
        sampledb.logic.groups.create_group(
            name=f"Basic Group {i}",
            description="",
            initial_user_id=user.id
        )
        for i in range(4)
    ]
    project_groups = [
        sampledb.logic.projects.create_project(
            name=f"Project Group {i}",
            description="",
            initial_user_id=user.id
        )
        for i in range(4)
    ]
    for other_user in other_users:
        sampledb.logic.default_permissions.set_default_permissions_for_user(user.id, other_user.id, sampledb.models.Permissions.READ)
    for basic_group in basic_groups:
        sampledb.logic.default_permissions.set_default_permissions_for_group(user.id, basic_group.id, sampledb.models.Permissions.READ)
    for project_group in project_groups:
        sampledb.logic.default_permissions.set_default_permissions_for_project(user.id, project_group.id, sampledb.models.Permissions.READ)
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'users/{user.id}/preferences')
    assert sampledb.logic.default_permissions.get_default_permissions_for_users(user.id) == {
        user.id: sampledb.models.Permissions.GRANT,
        other_users[0].id: sampledb.models.Permissions.READ,
        other_users[1].id: sampledb.models.Permissions.READ,
        other_users[2].id: sampledb.models.Permissions.READ,
        other_users[3].id: sampledb.models.Permissions.READ,
    }
    assert sampledb.logic.default_permissions.get_default_permissions_for_groups(user.id) == {
        basic_groups[0].id: sampledb.models.Permissions.READ,
        basic_groups[1].id: sampledb.models.Permissions.READ,
        basic_groups[2].id: sampledb.models.Permissions.READ,
        basic_groups[3].id: sampledb.models.Permissions.READ,
    }
    assert sampledb.logic.default_permissions.get_default_permissions_for_projects(user.id) == {
        project_groups[0].id: sampledb.models.Permissions.READ,
        project_groups[1].id: sampledb.models.Permissions.READ,
        project_groups[2].id: sampledb.models.Permissions.READ,
        project_groups[3].id: sampledb.models.Permissions.READ,
    }
    default_preferences_form = driver.find_element(By.CSS_SELECTOR, '#form-permissions')

    assert len(default_preferences_form.find_elements(By.CSS_SELECTOR, f'[name^="user_permissions-"][name$="-user_id"]')) == 5
    assert len(default_preferences_form.find_elements(By.CSS_SELECTOR, '[name^="group_permissions-"][name$="-group_id"]')) == 4
    assert len(default_preferences_form.find_elements(By.CSS_SELECTOR, '[name^="project_permissions-"][name$="-project_id"]')) == 4

    for other_user, permissions in zip(other_users, ["none", "read", "write", "grant"]):
        id_field = default_preferences_form.find_element(By.CSS_SELECTOR, f'[name^="user_permissions-"][name$="-user_id"][value="{other_user.id}"]')
        row = id_field.find_element(By.XPATH, "./ancestor::tr")
        row.find_element(By.CSS_SELECTOR, f'[name^="user_permissions-"][name$="-permissions"][value="{permissions}"]').click()

    for basic_group, permissions in zip(basic_groups, ["none", "read", "write", "grant"]):
        id_field = default_preferences_form.find_element(By.CSS_SELECTOR, f'[name^="group_permissions-"][name$="-group_id"][value="{basic_group.id}"]')
        row = id_field.find_element(By.XPATH, "./ancestor::tr")
        row.find_element(By.CSS_SELECTOR, f'[name^="group_permissions-"][name$="-permissions"][value="{permissions}"]').click()

    for project_group, permissions in zip(project_groups, ["none", "read", "write", "grant"]):
        id_field = default_preferences_form.find_element(By.CSS_SELECTOR, f'[name^="project_permissions-"][name$="-project_id"][value="{project_group.id}"]')
        row = id_field.find_element(By.XPATH, "./ancestor::tr")
        row.find_element(By.CSS_SELECTOR, f'[name^="project_permissions-"][name$="-permissions"][value="{permissions}"]').click()

    with wait_for_page_load(driver):
        default_preferences_form.find_element(By.CSS_SELECTOR, '[name="edit_permissions"]').click()

    assert sampledb.logic.default_permissions.get_default_permissions_for_users(user.id) == {
        user.id: sampledb.models.Permissions.GRANT,
        other_users[1].id: sampledb.models.Permissions.READ,
        other_users[2].id: sampledb.models.Permissions.WRITE,
        other_users[3].id: sampledb.models.Permissions.GRANT,
    }
    assert sampledb.logic.default_permissions.get_default_permissions_for_groups(user.id) == {
        basic_groups[1].id: sampledb.models.Permissions.READ,
        basic_groups[2].id: sampledb.models.Permissions.WRITE,
        basic_groups[3].id: sampledb.models.Permissions.GRANT,
    }
    assert sampledb.logic.default_permissions.get_default_permissions_for_projects(user.id) == {
        project_groups[1].id: sampledb.models.Permissions.READ,
        project_groups[2].id: sampledb.models.Permissions.WRITE,
        project_groups[3].id: sampledb.models.Permissions.GRANT,
    }