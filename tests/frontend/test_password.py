# coding: utf-8
"""

"""
import flask
import requests
import pytest
import bcrypt
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
from sampledb.logic.security_tokens import generate_token
from sampledb.logic.authentication import add_authentication_to_db


from tests.test_utils import flask_server, app


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        confirmed = True
        password = 'abc.123'
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        log = {
            'login': 'example@fz-juelich.de',
            'bcrypt_hash': pw_hash
        }
        add_authentication_to_db(log, sampledb.models.AuthenticationType.EMAIL, confirmed, user.id)
        # force attribute refresh
        assert user.id is not None
        # Check if authentication-method add to db
        with flask_server.app.app_context():
            assert len(sampledb.models.Authentication.query.all()) == 1
    return user


def test_login_failed_link_to_change_password_will_appear(flask_server):
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
        'password': 'xxx',
        'remember_me': False,
        'csrf_token': csrf_token
    })

    assert 'forgot your password?' in r.content.decode('utf-8')


def test_link_to_change_password(flask_server):
    session = requests.session()

    url = flask_server.base_url + 'users/password'
    r = session.get(url)
    assert r.status_code == 200

    assert 'send you a recovery link' in r.content.decode('utf-8')


def test_recovery_email_send(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    url = flask_server.base_url + 'users/password'
    r = session.get(url)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    #  send recovery email
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'email': 'example@fz-juelich.de',
            'csrf_token': csrf_token
        })
    assert r.status_code == 200

    # Check if an recovery mail was sent
    assert len(outbox) == 1
    assert 'example@fz-juelich.de' in outbox[0].recipients
    message = outbox[0].html
    assert 'Welcome to iffsample!' in message
