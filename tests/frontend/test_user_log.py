# coding: utf-8
"""

"""

import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic


from tests.test_utils import flask_server, app, app_context


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def other_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Other User", email="example2@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def test_get_current_user_log(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/me/activity')
    assert r.status_code == 200
    r = session.get(flask_server.base_url + 'users/me/activity', allow_redirects=False)
    assert r.status_code == 302
    assert 'Location' in r.headers
    url = r.headers['Location']
    assert url == flask_server.base_url + 'users/{}/activity'.format(user.id)


def test_get_user_log_empty(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'users/me/activity')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.findAll('ol', {'class': 'user-activity-log'})) == 1
    assert len(document.findAll('ol', {'class': 'user-activity-log'})[0].findAll('li')) == 0


def test_get_user_log(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    with flask_server.app.app_context():
        sampledb.logic.user_log.create_object(user_id=user.id, object_id=0)
    r = session.get(flask_server.base_url + 'users/me/activity')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.findAll('ol', {'class': 'user-activity-log'})) == 1
    assert len(document.findAll('ol', {'class': 'user-activity-log'})[0].findAll('li')) == 1


def test_get_other_user_log(flask_server, user, other_user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/{}/activity'.format(other_user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/42/activity').status_code == 404
