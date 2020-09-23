import pytest
import re
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic
from sampledb.logic.authentication import add_email_authentication


@pytest.fixture
def user_without_authentication(app):
    with app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
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
        add_email_authentication(user.id, 'example@fz-juelich.de', 'abc.123', True)
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
        add_email_authentication(user.id, 'example2@fz-juelich.de', 'abc.123', True)
        # force attribute refresh
        assert user.id is not None
        # Check if authentication-method add to db
        assert len(sampledb.models.Authentication.query.all()) > 0
    return user


def test_send_recovery_email_no_authentification_method(app, user_without_authentication):
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        # Send recovery email
        user = user_without_authentication
        users = []
        assert user is not None
        users.append(user)

        # no authentication_method
        sampledb.logic.utils.send_recovery_email(user.email)

        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_recovery_email(user.email)

        # check, if email was sent
        assert len(outbox) == 1
        assert user.email in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Account Recovery' in message
        assert 'There is no way to sign in to your SampleDB account' in message
    app.config['SERVER_NAME'] = server_name


def test_send_recovery_email_for_ldap_authentication(app):
    app.config['SERVER_NAME'] = 'localhost'
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
            sampledb.logic.utils.send_recovery_email(user.email)

        assert len(outbox) == 1
        assert user.email in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Account Recovery' in message
        assert 'You can use the {}'.format(app.config['LDAP_NAME']) in message


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
            sampledb.logic.utils.send_recovery_email(user.email)

        assert len(outbox) == 1
        assert 'example@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Account Recovery' in message
        assert 'click here' in message


def test_send_recovery_email_multiple_user_with_same_contact_email(app, user, user2):
    # Send recovery email
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        users = []
        users.append(user)
        users.append(user2)

        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_recovery_email(user.email)

        assert len(outbox) == 1
        assert 'example@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Account Recovery' in message
        assert 'click here' in message
        document = BeautifulSoup(message, 'html.parser')
        for user in users:
            preference_url = 'localhost/users/{}/preferences'.format(user.id)
            anchors = document.find_all('a', attrs={'href': re.compile(preference_url)})
            assert len(anchors) == 1
    app.config['SERVER_NAME'] = server_name