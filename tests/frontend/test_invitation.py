# coding: utf-8
"""

"""
import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
from sampledb.logic.security_tokens import generate_token


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        sampledb.logic.authentication.add_email_authentication(user.id, 'example@fz-juelich.de', 'abc.123', True)
        # force attribute refresh
        assert user.id is not None
        # Check if authentication-method add to db
        with flask_server.app.app_context():
            assert len(sampledb.models.Authentication.query.all()) == 1
    return user


def test_invitation_with_authenticated_user_is_possible(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    url = flask_server.base_url + 'users/invitation'
    r = session.get(url)
    assert r.status_code == 200

    assert 'invite a guest' in r.content.decode('utf-8') or 'invite another user' in r.content.decode('utf-8')


def test_send_invitation(flask_server, user):
    # Send a POST request to the invitation url
    # TODO: require authorization
    session = requests.session()

    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    url = flask_server.base_url + 'users/invitation'
    r = session.get(url)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form

    #  send invitation
    with sampledb.mail.record_messages() as outbox:
        r = session.post(url, {
            'email': 'user@example.com',
            'csrf_token': csrf_token
        })
    assert r.status_code == 200

    # Check if an invitation mail was sent
    assert len(outbox) == 1
    assert 'user@example.com' in outbox[0].recipients
    message = outbox[0].html
    assert 'SampleDB Invitation' in message

    # logout and test confirmation url
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False

    # Get the confirmation url from the mail and open it
    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[1].split('"')[0]
    assert confirmation_url.startswith(flask_server.base_url + 'users/invitation')
    r = session.get(confirmation_url)
    assert r.status_code == 200

    # Extract the CSRF token from the form so WTForms will accept out request
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']

    # Submit the missing information and complete the registration
    r = session.post(confirmation_url, {
        'email': 'user@example.com',
        'name': 'Testuser',
        'password': 'test',
        'password2': 'test',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    assert 'Your account has been created successfully.' in r.content.decode('utf-8')
    # check , if user is added to db
    with flask_server.app.app_context():
        assert len(sampledb.models.User.query.all()) == 2

    # test login
    with flask_server.app.app_context():
        assert sampledb.logic.authentication.login('user@example.com', 'test')


def test_registration_without_token_not_available(flask_server):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    url = flask_server.base_url + 'users/invitation'
    r = session.get(url)
    assert r.status_code == 403


def test_registration_with_wrong_token_403(flask_server):
    session = requests.session()
    token = generate_token('test@example.com', salt='user_invitation',
                           secret_key=flask_server.app.config['SECRET_KEY'])
    data = {'token': token}
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    url = flask_server.base_url + 'users/invitation'
    r = session.get(url, params=data)
    assert r.status_code == 403


def test_registration_with_token_available(flask_server):
    session = requests.session()
    # generate token
    token = generate_token('user@example.com', salt='invitation', secret_key=flask_server.app.config['SECRET_KEY'])
    data = {'token': token}
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False

    url = flask_server.base_url + 'users/invitation'
    r = session.get(url, params=data)
    assert r.status_code == 200

    assert 'Account Creation' in r.content.decode('utf-8')


def test_registration(flask_server):
    session = requests.session()
    # generate token
    token = generate_token('user@example.com', salt='invitation', secret_key=flask_server.app.config['SECRET_KEY'])
    data = {'token': token}
    url = flask_server.base_url + 'users/invitation'
    r = session.get(url, params=data)
    url = flask_server.base_url + 'users/invitation?token='+token
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']

    # Submit the missing information and complete the registration
    r = session.post(url, {
        'email': 'user@example.com',
        'name': 'Testuser',
        'password': 'test',
        'password2': 'test',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # check, if registrated user is added to db
    with flask_server.app.app_context():
        user = sampledb.models.users.User.query.filter_by(name="Testuser").one()

    assert user.email == "user@example.com"


def test_send_registration_with_wrong_invitation_email(flask_server):
    session = requests.session()
    # generate token
    token = generate_token('www@fz-juelich.de', salt='invitation',
                           secret_key=flask_server.app.config['SECRET_KEY'])
    data = {'token': token}
    url = flask_server.base_url + 'users/invitation'
    r = session.get(url, params=data)
    url = flask_server.base_url + 'users/invitation?token=' + token
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']

    with flask_server.app.app_context():
        len_old = len(sampledb.models.User.query.all())

    # Submit registration, invitation email changed in form registration
    r = session.post(url, {
        'email': 'wwwx@fz-juelich.de',
        'name': 'Testu',
        'password': 'test',
        'password2': 'test',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # check, if registrated user is not added to db
    with flask_server.app.app_context():
        assert len(sampledb.models.User.query.all()) == len_old


def test_send_registration_with_email_already_exists_in_authentication_method(flask_server, user):
    session = requests.session()

    # generate token
    token = generate_token('example@fz-juelich.de', salt='invitation',
                           secret_key=flask_server.app.config['SECRET_KEY'])
    data = {'token': token}
    url = flask_server.base_url + 'users/invitation'
    r = session.get(url, params=data)
    url = flask_server.base_url + 'users/invitation?token=' + token
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    assert document.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']

    with flask_server.app.app_context():
        len_old = len(sampledb.models.User.query.all())

    # Submit registration, invitation email changed in form registration
    r = session.post(url, {
        'email': 'example@fz-juelich.de',
        'name': 'Test',
        'password': 'test',
        'password2': 'test',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    assert 'There already is an account with this email address' in r.content.decode('utf-8')

