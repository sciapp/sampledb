import pytest
import bcrypt
import re
from bs4 import BeautifulSoup

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models
import sampledb.logic
from sampledb.logic.security_tokens import generate_token
from sampledb.logic.authentication import add_authentication_to_db


from ..test_utils import flask_server, app


@pytest.fixture
def user_without_authentication(app):
    with app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        print(user)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def user(app):
    with app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        confirmed = True
        password = 'abc.123'
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        log = {
            'login': 'example@fz-juelich.de',
            'bcrypt_hash': pw_hash
        }
        add_authentication_to_db(log, sampledb.models.AuthenticationType.EMAIL, confirmed, user.id)
        # force attribute refresh
        assert user.id is not None
        # Check if authentication-method add to db
        assert len(sampledb.models.Authentication.query.all()) > 0
    return user


@pytest.fixture
def user2(app):
    with app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        confirmed = True
        password = 'abc.123'
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        log = {
            'login': 'example@fz-juelich.de',
            'bcrypt_hash': pw_hash
        }
        add_authentication_to_db(log, sampledb.models.AuthenticationType.EMAIL, confirmed, user.id)
        # force attribute refresh
        assert user.id is not None
        # Check if authentication-method add to db
        assert len(sampledb.models.Authentication.query.all()) > 0
    return user



def test_send_recovery_email_with_wrong_parameters(app):
    with app.app_context():
        # Send recovery email
        username = app.config['TESTING_LDAP_LOGIN']
        password = app.config['TESTING_LDAP_PW']
        user = sampledb.logic.authentication.login(username, password)
        users = []
        assert user is not None

        result = sampledb.logic.utils.send_recovery_email(user.email, None, 'password')

        assert result is False

        result = sampledb.logic.utils.send_recovery_email(user.email, users, 'pw')

        assert result is False
        users.append(user)

        result = sampledb.logic.utils.send_recovery_email(user.email, users, 'pw')

        assert result is False

        result = sampledb.logic.utils.send_recovery_email('', users, 'pw')

        assert result is False

        result = sampledb.logic.utils.send_recovery_email(None, users, 'pw')

        assert result is False


def test_send_recovery_email_no_authentification_method(app, user_without_authentication):
    with app.app_context():
        # Send recovery email
        user = user_without_authentication
        users = []
        assert user is not None
        users.append(user)

        # not authentication_method
        result = sampledb.logic.utils.send_recovery_email(user.email, users, 'password')
        assert result is True

        # email authentication for ldap-user
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_recovery_email(user.email, users, 'password')

        # check, if email was sent
        assert len(outbox) == 1
        assert user.email in outbox[0].recipients
        message = outbox[0].html
        assert 'Recovery Request' in message
        assert 'There is no authentication-method found' in message


def test_send_recovery_email_for_ldap_authentication(app):
    with app.app_context():
        # Send recovery email
        username = app.config['TESTING_LDAP_LOGIN']
        password = app.config['TESTING_LDAP_PW']
        user = sampledb.logic.authentication.login(username, password)
        users = []
        assert user is not None
        users.append(user)

        # email authentication for ldap-user
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_recovery_email(user.email, users, 'password')

        assert len(outbox) == 1
        assert user.email in outbox[0].recipients
        message = outbox[0].html
        assert 'Recovery Request' in message
        assert 'You can use the PGI/JCNS' in message


def test_send_recovery_email_for_email_authentication(app, user):
    # Send recovery email
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        users = []
        assert user is not None
        users.append(user)
        users = []
        users.append(user)

        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_recovery_email(user.email, users, 'password')

        assert len(outbox) == 1
        assert 'example@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'Recovery Request' in message
        assert 'Click this link to reset the password' in message


def test_send_recovery_email_multiple_user_with_same_contact_email(app, user, user2):
    # Send recovery email
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        users = []
        users.append(user)
        users.append(user2)

        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_recovery_email(user.email, users, 'password')

        assert len(outbox) == 1
        assert 'example@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'Recovery Request' in message
        assert 'Click this link to reset the password' in message
        document = BeautifulSoup(message, 'html.parser')
        for user in users:
            preference_url = 'localhost/users/{}/preferences'.format(user.id)
            anchors = document.find_all('a', attrs={'href': re.compile(preference_url)})
            assert len(anchors) == 1