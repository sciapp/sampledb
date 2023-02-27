import pytest
import requests

import sampledb


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
    return user


def test_index_translation(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url)
    assert r.status_code == 200
    assert 'Welcome'.encode('utf-8') in r.content
    r = session.get(flask_server.base_url, headers={"Accept-Language": "de"})
    assert r.status_code == 200
    assert 'Welcome'.encode('utf-8') not in r.content
    assert 'Willkommen'.encode('utf-8') in r.content
