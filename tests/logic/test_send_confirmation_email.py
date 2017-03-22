import pytest
import bcrypt
from bs4 import BeautifulSoup

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models


from ..test_utils import  flask_server, app

@pytest.fixture
def users(app):
    with app.app_context():
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

def test_send_confirm_email(app):
    # Submit the missing information and complete the registration

    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        username = app.config['TESTING_LDAP_LOGIN']
        password = app.config['TESTING_LDAP_PW']
        user = sampledb.logic.authentication.login(username, password)
        assert user is not None

        # email authentication for ldap-user
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_confirm_email(user.email, user.id, 'add_login')

        assert len(outbox) == 1
        assert 'd.henkel@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'Welcome to iffsample!' in message

        # email invitation new user
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_confirm_email('test@fz-juelich.de', None, 'invitation')

        assert len(outbox) == 1
        assert 'test@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'Welcome to iffsample!' in message

        # confirm new contact_email
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_confirm_email('testmail@fz-juelich.de', 1, 'edit_profile')

        assert len(outbox) == 1
        assert 'testmail@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'Welcome to iffsample!' in message

