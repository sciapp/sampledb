import pytest
import bcrypt
from bs4 import BeautifulSoup

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models

from ..test_utils import app_context, flask_server, app

@pytest.fixture
def users():
    names = ['User 1', 'User 2']
    users = [User(name=name, email="example@fz-juelich.de", type=UserType.PERSON) for name in names]
    password = 'test123'
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    log = {
        'login': 'example@fz-juelich.de',
        'bcrypt_hash': pw_hash
    }
    log1 = {
        'login': 'example1@fz-juelich.de',
        'bcrypt_hash': pw_hash
    }
    confirmed = False
    for user in users:
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
        if not confirmed:
            auth = Authentication(log, AuthenticationType.OTHER, confirmed, user.id)
        else:
            auth = Authentication(log1, AuthenticationType.OTHER, confirmed, user.id)
        confirmed = True
        sampledb.db.session.add(auth)
        sampledb.db.session.commit()
        assert Authentication.id is not None

    user = User(name='Experiment 1', email="example@fz-juelich.de", type=UserType.OTHER)
    users.append(user)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    log = {
        'login': 'ombe',
        'bcrypt_hash': pw_hash
    }
    # force attribute refresh

    auth = Authentication(log, AuthenticationType.OTHER, True, user.id)
    sampledb.db.session.add(auth)
    sampledb.db.session.commit()

    return users

def get_authentication_methods(userid):
    return Authentication.query.get(userid)


def test_login_user(flask_server, users):

    name = users[0].id
    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.login(username,password)
    assert user is not None

    user = sampledb.logic.authentication.login('example1@fz-juelich.de', 'test123')
    # user is confirmed
    assert user is not None

    user = sampledb.logic.authentication.login('example@fz-juelich.de', 'test123')
    # user is not confirmed
    assert user is None

    user = sampledb.logic.authentication.login('ombe', 'test123')
    # user is confirmed
    assert user is not None

    user = sampledb.logic.authentication.login('testmail@fz-juelich.de', 'test123')
    # user is not confirmed
    assert user is None

    user = sampledb.logic.authentication.login('henkel', 'test123')
    # user is not confirmed
    assert user is None


def test_add_login(flask_server, users):
    auth = get_authentication_methods(3)
    user = sampledb.logic.authentication.add_login(3, 'ombe', 'abc', auth)
    # already exists
    assert user is False

    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.add_login(1, username, password, AuthenticationType.LDAP)
    assert user is True

    user = sampledb.logic.authentication.add_login(1, username, 'xxx', AuthenticationType.LDAP)
    # password wrong
    assert user is False

    user = sampledb.logic.authentication.add_login(3, "web.de", 'abc123', AuthenticationType.EMAIL)
    # no email
    assert user is False
