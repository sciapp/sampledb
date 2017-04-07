import pytest
import bcrypt
from bs4 import BeautifulSoup

from sampledb.models import User, UserType,  Authentication, AuthenticationType
from sampledb.logic.ldap import LdapAccountAlreadyExist, LdapAccountOrPasswordWrong
from sampledb.logic.authentication import AuthenticationMethodWrong, OnlyOneAuthenticationMethod, check_count_of_authentication_methods

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
    user = sampledb.logic.authentication.login(username, password)
    assert user is not None

    user = sampledb.logic.authentication.login('example1@fz-juelich.de', 'test123')
    # user is confirmed
    assert user is not None

    user = sampledb.logic.authentication.login('example@fz-juelich.de', 'test123')
    # user is not confirmed
    assert user is None

    user = sampledb.logic.authentication.login('ombe', 'test123')
    # user is confirmed and experiment
    assert user is not None

    user = sampledb.logic.authentication.login('testmail@fz-juelich.de', 'test123')
    # user is not in db
    assert user is None

    user = sampledb.logic.authentication.login('henkel', 'test123')
    # user is in ldap, password wrong
    assert user is None


def test_add_login(flask_server, users):
    auth = get_authentication_methods(3)
    with pytest.raises(LdapAccountAlreadyExist) as excinfo:
        user = sampledb.logic.authentication.add_login(3, 'ombe', 'abc', auth)
    # already exists
    assert 'Ldap-Account already exists' in str(excinfo.value)

    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.add_login(1, username, password, AuthenticationType.LDAP)
    assert user is True

    with pytest.raises(LdapAccountOrPasswordWrong) as excinfo:
        user = sampledb.logic.authentication.add_login(1, 'henkel', 'xxx', AuthenticationType.LDAP)
    # password wrong
    assert 'Ldap login or password wrong'

    with pytest.raises(AuthenticationMethodWrong) as excinfo:
        user = sampledb.logic.authentication.add_login(3, "web.de", 'abc123', AuthenticationType.EMAIL)
    # no email
    assert 'Login must be an email if the authentication_method is email'


def test_check_count_of_authentication_methods(flask_server, users):
    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.login(username, password)
    assert user is not None

    with pytest.raises(OnlyOneAuthenticationMethod) as excinfo:
         erg = check_count_of_authentication_methods(user.id)

    assert('one authentication-method must at least exist, delete not possible')