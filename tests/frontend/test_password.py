# coding: utf-8
"""

"""
import re
import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_email_authentication(user.id, 'example@fz-juelich.de', 'abc.123')
        # force attribute refresh
        assert user.id is not None
        # Check if authentication-method add to db
        assert len(sampledb.models.Authentication.query.all()) == 1
    return user


@pytest.fixture
def user_without_authentication(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example1@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def test_login_failed_link_to_change_password_will_appear(flask_server):
    session = requests.session()
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('a', {'href': '/users/me/preferences'}) is not None


def test_recovery_email_send_no_authentication_method_exists(flask_server, user_without_authentication):
    user = user_without_authentication
    session = requests.session()

    url = flask_server.base_url + 'users/me/preferences'
    r = session.get(url)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('form', {'id': 'form-request-password-reset'}) is not None

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    #  send recovery email
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'email': 'example1@fz-juelich.de',
            'csrf_token': csrf_token
        })
    assert r.status_code == 200

    # Check if an recovery mail was sent, No authentication-method exist
    assert len(outbox) == 1
    message = outbox[0].html
    assert 'There is no way to sign in to your SampleDB account' in message


def test_new_password_send(flask_server, user):
    session = requests.session()
    url = flask_server.base_url + 'users/me/preferences'
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

    # Check if a recovery mail was sent
    assert len(outbox) == 1
    message = outbox[0].html
    document = BeautifulSoup(message, 'html.parser')
    preference_url = flask_server.base_url + 'users/{}/preferences'.format(user.id)
    anchors = document.find_all('a', attrs={'href': re.compile(preference_url)})
    assert len(anchors) == 1
    anchor = anchors[0]
    url = anchor.get('href')
    r = session.get(url)

    assert r.status_code == 200
    assert 'Account Recovery for Basic User' in r.content.decode('utf-8')
    assert 'New Password' in r.content.decode('utf-8')

    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']

    r = session.post(url, {
        'password': 'test',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    with flask_server.app.app_context():
        assert sampledb.logic.authentication.login('example@fz-juelich.de', 'test')

