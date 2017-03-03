# coding: utf-8
"""

"""

import requests
import pytest
import sqlalchemy
from bs4 import BeautifulSoup

import sampledb
import sampledb.authentication.models

from .utils import flask_server


@pytest.fixture
def app():
    sampledb_app = sampledb.create_app()
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
    assert confirmation_url.startswith(flask_server.base_url + 'confirm/')
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
    # Currently there is no way to know whether we're authenticated

    # Log out again
    r = session.get(flask_server.base_url + 'logout')
    assert r.status_code == 200


def test_useradd(flask_server):
    session = requests.session()
    r = session.get(flask_server.base_url + 'add_user')
    url = flask_server.base_url + 'add_user'
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    # Try to add user
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