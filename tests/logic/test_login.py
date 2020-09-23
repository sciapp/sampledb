import pytest
import bcrypt

from sampledb.models import User, UserType,  Authentication, AuthenticationType
from sampledb.logic.errors import AuthenticationMethodWrong, OnlyOneAuthenticationMethod, \
    AuthenticationMethodAlreadyExists, LDAPAccountAlreadyExistError, LDAPAccountOrPasswordWrongError
from sampledb.logic.authentication import remove_authentication_method, change_password_in_authentication_method
import sampledb
import sampledb.models


@pytest.fixture
def users():
    names = ['User 1', 'User 2']
    users = [User(name=name, email="user@example.com", type=UserType.PERSON) for name in names]
    password = 'test123'
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    log = {
        'login': 'unconfirmed_user@example.com',
        'bcrypt_hash': pw_hash
    }
    log1 = {
        'login': 'confirmed_user@example.com',
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

    user = User(name='Experiment 1', email="experiment@example.com", type=UserType.OTHER)
    users.append(user)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    log = {
        'login': 'experiment_account',
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

    user = sampledb.logic.authentication.login('confirmed_user@example.com', 'test123')
    # user is confirmed
    assert user is not None

    user = sampledb.logic.authentication.login('unconfirmed_user@example.com', 'test123')
    # user is not confirmed
    assert user is None

    user = sampledb.logic.authentication.login('experiment_account', 'test123')
    # user is confirmed and experiment
    assert user is not None

    user = sampledb.logic.authentication.login('unknown_user@example.com', 'test123')
    # user is not in db
    assert user is None

    user = sampledb.logic.authentication.login('username', 'test123')
    # user is in ldap, password wrong
    assert user is None


def test_add_login_ldap(flask_server, users):
    with pytest.raises(LDAPAccountOrPasswordWrongError) as excinfo:
        sampledb.logic.authentication.add_authentication_method(1, 'new_user', 'password', AuthenticationType.LDAP)
    # wrong password
    assert 'Ldap login or password wrong' in str(excinfo.value)

    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.add_authentication_method(1, username, password, AuthenticationType.LDAP)
    assert user is True

    with pytest.raises(LDAPAccountAlreadyExistError) as excinfo:
        user = sampledb.logic.authentication.add_authentication_method(1, 'new_user', 'password', AuthenticationType.LDAP)
    # no second ldap authentication possible
    assert 'Ldap-Account already exists'


def test_add_login(flask_server, users):
    with pytest.raises(AuthenticationMethodWrong) as excinfo:
        user = sampledb.logic.authentication.add_authentication_method(3, "example.com", 'password', AuthenticationType.EMAIL)
    # no email
    assert 'Login must be a valid email address'

    # add authentication-method without password not allowed
    result = sampledb.logic.authentication.add_authentication_method(3, "new_user@example.com", '', AuthenticationType.EMAIL)
    assert result is False

    # add authentication-method without login not allowed
    result = sampledb.logic.authentication.add_authentication_method(3, None, 'password', AuthenticationType.EMAIL)
    assert result is False

    # add authentication-method without login not allowed
    result = sampledb.logic.authentication.add_authentication_method(3, 'new_user@example.com', 'password', None)
    assert result is False


def test_add_login_email(app, users):
    # add authentication-method email
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        result = sampledb.logic.authentication.add_authentication_method(3, 'new_user@example.com', 'xxx', AuthenticationType.EMAIL)
        assert result is True
    app.config['SERVER_NAME'] = server_name


def test_add_login_other_not_allowed(flask_server, users):
    # add other authentication-method not allowed
    result = sampledb.logic.authentication.add_authentication_method(3, "experiment", 'abc123', AuthenticationType.OTHER)
    assert result is False


def test_add_login_email_method_already_exists(flask_server, users):
    with pytest.raises(AuthenticationMethodAlreadyExists) as excinfo:
        user = sampledb.logic.authentication.add_authentication_method(1, 'confirmed_user@example.com', 'abc', AuthenticationType.EMAIL)
    assert 'An authentication method with this login already exists' in str(excinfo.value)


def test_remove_authentication_method(flask_server, users):
    user = users[0]
    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']

    with pytest.raises(OnlyOneAuthenticationMethod) as excinfo:
        remove_authentication_method(1)

    assert 'one authentication-method must at least exist, delete not possible' in str(excinfo.value)

    sampledb.logic.authentication.add_authentication_method(user.id, username, password, AuthenticationType.LDAP)

    assert len(user.authentication_methods) == 2
    authentication_id = user.authentication_methods[0].id
    result = remove_authentication_method(authentication_id)

    assert len(user.authentication_methods) == 1


def test_change_password_in_authentication_method(flask_server, users):
    result = change_password_in_authentication_method(10, 'abc')
    # authentication_method_id not exist
    assert result is False

    result = change_password_in_authentication_method(10, '')
    # password empty
    assert result is False

    result = change_password_in_authentication_method(1, 'xxxx')
    # password will be changed
    assert result is True

    username = flask_server.app.config['TESTING_LDAP_LOGIN']
    password = flask_server.app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.login(username, password)
    assert user is not None

    authentication_id = user.authentication_methods[0].id
    result = change_password_in_authentication_method(authentication_id, 'abc')
    # authentication_method is LDAP, password not changed
    assert result is False

    user_id = users[2].id
    user = users[2]
    authentication_id = user.authentication_methods[0].id
    result = change_password_in_authentication_method(authentication_id, 'abc')
    # change password if authentication_method is OTHER
    assert result is True


def test_is_login_available(flask_server, users):
    assert sampledb.logic.authentication.is_login_available('test')
    sampledb.logic.authentication.add_other_authentication(users[0].id, 'test', 'test')
    assert not sampledb.logic.authentication.is_login_available('test')
