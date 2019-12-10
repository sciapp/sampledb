import pytest
import bcrypt
from bs4 import BeautifulSoup

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models
import sampledb.logic


from ..test_utils import flask_server, app


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
        assert sampledb.logic.ldap.create_user_from_ldap(username).email in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Email Confirmation' in message

        # email invitation new user
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_confirm_email('test@fz-juelich.de', None, 'invitation')

        assert len(outbox) == 1
        assert 'test@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Email Confirmation' in message

        # confirm new contact_email
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_confirm_email('testmail@fz-juelich.de', 1, 'edit_profile')

        assert len(outbox) == 1
        assert 'testmail@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Email Confirmation' in message


