# coding: utf-8
"""

"""

import requests
from bs4 import BeautifulSoup

import sampledb
import sampledb.models

from tests.test_utils import flask_server, app


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
        assert len(sampledb.models.User.query.all()) == 1

    #  test second Submit the missing information
    r = session.post(confirmation_url, {
        'name': 'Testuser',
        'password': 'test',
        'password2': 'test',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200

    r = session.get(flask_server.base_url + 'users/me/sign_in')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # Try logging in
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': 'example@fz-juelich.de',
        'password': 'test',
        'remember_me': False,
        'csrf_token': csrf_token
    })

    assert r.status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True


def test_useradd(flask_server):
    session = requests.session()
    url = flask_server.base_url + 'add_user'
    r = session.get(url)
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    r = session.post(url, {
        'name': 'ombe',
        'email': 'd.henkel@fz-juelich.de',
        'password': 'xxxs',
        'login': 'ombe',
        'type': 'O',
        'authentication_method': 'O',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    with flask_server.app.app_context():
        assert len(sampledb.models.User.query.all()) == 1

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



