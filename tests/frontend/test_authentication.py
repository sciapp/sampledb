# coding: utf-8
"""

"""

import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def test_sign_in(flask_server):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    # initially, the a link to the sign in page will be displayed
    r = session.get(flask_server.base_url)
    assert r.status_code == 200
    assert '/users/me/sign_in' in r.content.decode('utf-8')
    # the sign in page contains a form with fields for username, password and a remember_me checkbox
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
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True


def test_sign_in_redirect(flask_server):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    # initially, the a link to the sign in page will be displayed
    r = session.get(flask_server.base_url)
    assert r.status_code == 200
    assert '/users/me/sign_in' in r.content.decode('utf-8')
    # the sign in page contains a form with fields for username, password and a remember_me checkbox
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
    r = session.post(flask_server.base_url + 'users/me/sign_in?next=/actions/', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': False,
        'csrf_token': csrf_token
    }, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'] == flask_server.base_url + 'actions/'
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True


def test_sign_in_invalid_redirect(flask_server):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    # initially, the a link to the sign in page will be displayed
    r = session.get(flask_server.base_url)
    assert r.status_code == 200
    assert '/users/me/sign_in' in r.content.decode('utf-8')
    # the sign in page contains a form with fields for username, password and a remember_me checkbox
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
    r = session.post(flask_server.base_url + 'users/me/sign_in?next=http://google.de/', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': flask_server.app.config['TESTING_LDAP_PW'],
        'remember_me': False,
        'csrf_token': csrf_token
    }, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'] == flask_server.base_url
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True


def test_sign_in_invalid_password(flask_server):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    # get the csrf token
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'password': 'invalid',
        'remember_me': False,
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False


def test_sign_in_missing_password(flask_server):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    # get the csrf token
    r = session.get(flask_server.base_url + 'users/me/sign_in')
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_in', {
        'username': flask_server.app.config['TESTING_LDAP_LOGIN'],
        'remember_me': False,
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False


def test_sign_in_authenticated(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    # when already authenticated, the sign in page should instantly redirect
    r = session.get(flask_server.base_url + 'users/me/sign_in', allow_redirects=False)
    assert r.status_code == 302


def test_sign_out_navbar(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True
    # when logged in, the navbar contains a sign out form
    r = session.get(flask_server.base_url + '')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    sign_out_form = document.find('form', {'action': '/users/me/sign_out', 'method': 'post'})
    assert sign_out_form is not None
    # the form contains a submit button
    assert sign_out_form.find('button', {'type': 'submit'}) is not None
    # it also contains a hidden CSRF token
    assert sign_out_form.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = sign_out_form.find('input', {'name': 'csrf_token', 'type': 'hidden'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_out', {
        'csrf_token': csrf_token
    })
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False


def test_sign_out_page(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True
    # when logged in, the sign out page contains a sign out form
    r = session.get(flask_server.base_url + 'users/me/sign_out')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    sign_out_form = document.find('form', {'action': '/users/me/sign_out', 'method': 'post'})
    assert sign_out_form is not None
    # the form contains a submit button
    assert sign_out_form.find('button', {'type': 'submit'}) is not None
    # it also contains a hidden CSRF token
    assert sign_out_form.find('input', {'name': 'csrf_token', 'type': 'hidden'}) is not None
    csrf_token = sign_out_form.find('input', {'name': 'csrf_token', 'type': 'hidden'})['value']
    # submit the form
    r = session.post(flask_server.base_url + 'users/me/sign_out', {
        'csrf_token': csrf_token
    })
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False


def test_sign_out_page_unauthenticated(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False
    # when not authenticated, the sign out page redirects to the sign in page
    r = session.get(flask_server.base_url + 'users/me/sign_out', allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].startswith(flask_server.base_url + 'users/me/sign_in')
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is False

