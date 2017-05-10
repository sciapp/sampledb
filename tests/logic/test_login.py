import pytest
import bcrypt
from bs4 import BeautifulSoup

from sampledb.models import User, UserType,  Authentication, AuthenticationType
from sampledb.logic.ldap import LdapAccountAlreadyExist, LdapAccountOrPasswordWrong
from sampledb.logic.authentication import AuthenticationMethodWrong, OnlyOneAuthenticationMethod, AuthenticationMethodAlreadyExists
from sampledb.logic.authentication import remove_authentication_method, change_password_in_authentication_method, get_authentication_method_id_of_login_of_user
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
            auth = Authentication(log, AuthenticationType.EMAIL, confirmed, user.id)
        else:
            auth = Authentication(log1, AuthenticationType.EMAIL, confirmed, user.id)
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
    with pytest.raises(LdapAccountOrPasswordWrong) as excinfo:
        sampledb.logic.authentication.add_login(1, 'henkel', 'abc', AuthenticationType.LDAP)
    # wrong password
    assert 'Ldap login or password wrong' in str(excinfo.value)

    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.add_login(1, username, password, AuthenticationType.LDAP)
    assert user is True

    with pytest.raises(LdapAccountAlreadyExist) as excinfo:
        user = sampledb.logic.authentication.add_login(1, 'henkel', 'xxx', AuthenticationType.LDAP)
    # no second ldap authentification possible
    assert 'Ldap-Account already exists'

    with pytest.raises(AuthenticationMethodWrong) as excinfo:
        user = sampledb.logic.authentication.add_login(3, "web.de", 'abc123', AuthenticationType.EMAIL)
    # no email
    assert 'Login must be an email if the authentication_method is email'


def test_add_login_email_method_already_exists(flask_server, users):
    with pytest.raises(AuthenticationMethodAlreadyExists) as excinfo:
        user = sampledb.logic.authentication.add_login(1, 'example1@fz-juelich.de', 'abc', AuthenticationType.EMAIL)
    assert 'This Email-authentication-method already exists' in str(excinfo.value)


def test_remove_authentication_method(flask_server, users):
    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.login(username, password)
    assert user is not None

    with pytest.raises(OnlyOneAuthenticationMethod) as excinfo:
        remove_authentication_method(user.id, 1)

    assert 'one authentication-method must at least exist, delete not possible' in str(excinfo.value)

    sampledb.logic.authentication.add_login(user.id, 'test', 'xxx', AuthenticationType.OTHER)


    assert len(user.authentication_methods) == 2
    authentication_id = get_authentication_method_id_of_login_of_user(user.id, username)
    result = remove_authentication_method(user.id, authentication_id)


    assert len(user.authentication_methods) == 1


def test_change_password_in_authentication_method(flask_server, users):

    user_id = users[0].id
    result = change_password_in_authentication_method(user_id, 10, 'abc')
    # authentication_method_id not exist
    assert result is False

    result = change_password_in_authentication_method(user_id, None, 'abc')
    # authentication_method_id is None
    assert result is False

    result = change_password_in_authentication_method(None, 1, 'abc')
    # user_id is None
    assert result is False

    result = change_password_in_authentication_method(user_id, 10, '')
    # password empty
    assert result is False

    result = change_password_in_authentication_method(user_id, 1, 'xxxx')
    # password will be changed
    assert result is True

    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.login(username, password)
    assert user is not None
    user_id = user.id
    authentication_id = get_authentication_method_id_of_login_of_user(user_id, username)
    result = change_password_in_authentication_method(user_id, authentication_id, 'abc')
    # authentication_method is LDAP, password not changed
    assert result is False

    user_id = users[2].id
    authentication_id = get_authentication_method_id_of_login_of_user(user_id, 'ombe')
    result = change_password_in_authentication_method(user_id, authentication_id, 'abc')
    # change password if authentication_method is OTHER
    assert result is True


def test_get_authentication_method_id_of_login_of_user(flask_server, users):

    user_id = users[0].id
    result = get_authentication_method_id_of_login_of_user(user_id, '')
    # authentication_method_login is empty
    assert result is False

    result = get_authentication_method_id_of_login_of_user(0, 'example@fz-juelich.de')
    # authentication_method_login is empty
    assert result is False

    result = get_authentication_method_id_of_login_of_user(None, 'example@fz-juelich.de')
    # authentication_method_login is empty
    assert result is False

    result = get_authentication_method_id_of_login_of_user(user_id, 'example@fz-juelich.de')
    assert result == 1



