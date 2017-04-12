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



