import pytest
import bcrypt

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models
import sampledb.logic


@pytest.fixture
def users(app):
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
    return users


def test_build_recovery_url_with_wrong_parameter(users):
    # build recovery_url_of_every_authentication_method not possible
    authentication_method = Authentication.query.filter(Authentication.user_id == users[0].id).first()
    with pytest.raises(Exception):
        sampledb.logic.utils.build_confirm_url(None)


def test_build_recovery_url_email(app, users):
    # build recovery_url_of_every_authentication_method
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        authentication_method = Authentication.query.filter(Authentication.user_id == users[0].id).first()
        confirm_url = sampledb.logic.utils.build_confirm_url(authentication_method)
        assert confirm_url.startswith('http://localhost/users')
    app.config['SERVER_NAME'] = server_name


def test_build_recovery_url_ldap(app, users):
    # build recovery_url_of_every_authentication_method
    username = app.config['TESTING_LDAP_LOGIN']
    password = app.config['TESTING_LDAP_PW']
    user = sampledb.logic.authentication.login(username, password)
    assert user is not None

    authentication_method = Authentication.query.filter(Authentication.user_id == user.id).first()
    with pytest.raises(AssertionError):
        sampledb.logic.utils.build_confirm_url(authentication_method)

