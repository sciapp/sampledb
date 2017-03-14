# coding: utf-8
"""

"""

import requests
import pytest
import sqlalchemy
from bs4 import BeautifulSoup
import flask
import flask_login

import sampledb
import sampledb.authentication.models

from .utils import flask_server


@pytest.fixture
def app():
    sampledb_app = sampledb.create_app()

    @sampledb_app.route('/users/me/loginstatus')
    def check_login():
        return flask.jsonify(flask_login.current_user.is_authenticated)

    db_url = sampledb_app.config['SQLALCHEMY_DATABASE_URI']
    engine = sampledb.db.create_engine(db_url)
    # fully empty the database first
    sqlalchemy.MetaData(reflect=True, bind=engine).drop_all()
    # recreate the tables used by this application
    with sampledb_app.app_context():
        sampledb.db.metadata.create_all(bind=engine)

    return sampledb_app


def test_index(flask_server):
    r = requests.get(flask_server.base_url)
    assert r.status_code == 200


def test_invite(flask_server):
    # Send a POST request to the invitation url
    # TODO: require authorization
    session = requests.session()
    with sampledb.mail.record_messages() as outbox:
        r = session.post(flask_server.base_url + 'invite_user', data={'mail': 'example@fz-juelich.de'})
        assert r.status_code == 200

    # Check if an invitation mail was sent
    assert len(outbox) == 1
    assert 'example@fz-juelich.de' in outbox[0].recipients
    message = outbox[0].html
    assert 'Welcome to iffsample!' in message

    # Get the confirmation url from the mail and open it
    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[1].split('"')[0]
    assert confirmation_url.startswith(flask_server.base_url + 'confirm')
    r = session.get(confirmation_url)
    assert r.status_code == 200

    # Extract the CSRF token from the form so WTForms will accept out request
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']

    # Submit the missing information and complete the registration
    r = session.post(confirmation_url, {
        'name': 'Testuser',
        'password': 'test',
        'password2': 'test',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    assert 'registration successful' in r.content.decode('utf-8')
    # check , if user is added to db
    with flask_server.app.app_context():
        assert len(sampledb.authentication.models.User.query.all()) == 1

    #  test second Submit the missing information
    r = session.post(confirmation_url, {
        'name': 'Testuser',
        'password': 'test',
        'password2': 'test',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200


    # Try logging in
    r = session.post(flask_server.base_url + 'login', {
        'username': 'example@fz-juelich.de',
        'password': 'test'
    })
    assert r.status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    r = session.post(flask_server.base_url + 'authentication/add/1')
    assert r.status_code == 200

    url = flask_server.base_url + 'authentication/add/1'
    r = session.get(url)
    assert r.status_code == 200

    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    # Submit the missing information and complete the registration
    # add correct authentication-method

    r = session.post(url, {
        'login': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'authentication_method': 'L',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # add incorrect authentication-method

    r = session.post(url, {
        'login': 'henkel',
        'password': 'xxx',
        'authentication_method': 'L',
        'csrf_token': csrf_token
    })
    assert r.status_code == 400

    # Create new session
    session = requests.session()

    # Try to login
    r = session.post(flask_server.base_url + 'login', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW']
    })
    assert r.status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    # Log out again
    r = session.get(flask_server.base_url + 'logout')
    assert r.status_code == 200


def test_useradd(flask_server):
    session = requests.session()
    url = flask_server.base_url + 'add_user'
    r = session.get(url)
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    r = session.post(url, {
        'name': 'ombe',
        'email': 'd.henkel@fz-juelich.de',
        'password': 'xxx',
        'login': 'ombe',
        'type': 'O',
        'authentication_method': 'O',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    with flask_server.app.app_context():
        assert len(sampledb.authentication.models.User.query.all()) == 1

    # Try to add user twice
    r = session.post(url, {
        'name': 'ombe',
        'email': 'd.henkel@fz-juelich.de',
        'password': 'xxxx',
        'login': 'ombe',
        'type': 'O',
        'authentication_method': 'O',
        'admin': '0',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200


def test_ldap_authentification(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.post(flask_server.base_url + 'login', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW']
    })
    assert r.status_code == 200


def test_show_all(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.post(flask_server.base_url + 'login', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW']
    })
    assert r.status_code == 200

    r = session.get(flask_server.base_url + 'login/show_all')
    assert r.status_code == 200

def test_remove_authenticationmethod(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.post(flask_server.base_url + 'login', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW']
    })
    assert r.status_code == 200
    r = session.post(flask_server.base_url + 'authentication/1/remove/1')
    assert r.status_code == 200

def test_add_authenticationmethod(flask_server):
    # Try logging in with ldap-test-account
    session = requests.session()
    r = session.post(flask_server.base_url + 'login', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW']
    })
    assert r.status_code == 200
    r = session.post(flask_server.base_url + 'authentication/add/1')
    assert r.status_code == 200

    url = flask_server.base_url + 'authentication/add/1'
    r = session.get(url)
    assert r.status_code == 200

    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    # Submit the missing information and complete the registration
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'login': 'example@fz-juelich.de',
            'password': 'xxx',
            'authentication_method': 'E',
            'csrf_token': csrf_token
        })
    assert r.status_code == 200

    # Check if authentication-method add to db
    with flask_server.app.app_context():
        assert len(sampledb.authentication.models.Authentication.query.all()) ==2

    # Create new session
    session = requests.session()

    # Try to login , expect 401 because the confiramtion mail is later
    r = session.post(flask_server.base_url + 'login', {
        'username': 'example@fz-juelich.de',
        'password': 'xxx'
    })
    assert r.status_code == 401
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False

    # Check if an confirmation mail was sent
    assert len(outbox) == 1
    assert 'example@fz-juelich.de' in outbox[0].recipients
    message = outbox[0].html
    assert 'Welcome to iffsample!' in message

    # Get the confirmation url from the mail and open it
    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[1].split('"')[0]
    assert confirmation_url.startswith(flask_server.base_url + 'confirm-email')
    r = session.get(confirmation_url)
    assert r.status_code == 200

    # Try to login

    r = session.post(flask_server.base_url + 'login', {
        'username': 'example@fz-juelich.de',
        'password': 'xxx'
    })
    assert r.status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    r = session.post(flask_server.base_url + 'authentication/1/remove/1')
    assert r.status_code == 200


def test_confirm_email(flask_server):
    session = requests.session()
    r = session.post(flask_server.base_url + 'login', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW']
    })
    url = flask_server.base_url + 'edit_profile'
    assert r.status_code == 200
    # Send a POST request to the confirmation url
    # TODO: require authorization

    r = session.get(flask_server.base_url + 'edit_profile')
    assert r.status_code == 200

    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']

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
    print(confirmation_url)
    assert confirmation_url.startswith(flask_server.base_url + 'confirm-email')
    r = session.get(confirmation_url)
    assert r.status_code == 200
