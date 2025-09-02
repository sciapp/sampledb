import time

import sampledb
import sampledb.models
import sampledb.logic

from ..conftest import wait_for_background_task


def test_send_confirm_email(app, enable_background_tasks):
    # Submit the missing information and complete the registration

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        username = app.config['TESTING_LDAP_LOGIN']
        password = app.config['TESTING_LDAP_PW']
        user = sampledb.logic.authentication.login(username, password)
        assert user is not None

        _, task = sampledb.logic.utils.send_email_confirmation_email(user.email, user.id, 'add_login')
        assert task is not None
        assert task.type == 'send_mail'
        assert task.data['subject'] == "SampleDB Email Confirmation"

        wait_for_background_task(task)

        assert task.status == sampledb.models.BackgroundTaskStatus.DONE
        sampledb.db.session.delete(task)
        sampledb.db.session.commit()

        sampledb.logic.utils.send_user_invitation_email('test@example.com', 0)

        task = sampledb.models.BackgroundTask.query.filter_by(type="send_mail").first()

        assert task is not None
        assert task.type == 'send_mail'
        assert task.data['subject'] == "SampleDB Invitation"

        wait_for_background_task(task)

        assert task.status == sampledb.models.BackgroundTaskStatus.DONE

        app.config['ENABLE_BACKGROUND_TASKS'] = False
        # email authentication for ldap-user
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_email_confirmation_email(user.email, user.id, 'add_login')

        assert len(outbox) == 1
        assert sampledb.logic.ldap.create_user_from_ldap(username).email in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Email Confirmation' in message

        # email invitation new user
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_user_invitation_email('test@example.com', 0)

        assert len(outbox) == 1
        assert 'test@example.com' in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Invitation' in message

        # confirm new contact_email
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_email_confirmation_email('testmail@example.com', 1, 'edit_profile')

        assert len(outbox) == 1
        assert 'testmail@example.com' in outbox[0].recipients
        message = outbox[0].html
        assert 'SampleDB Email Confirmation' in message
    app.config['SERVER_NAME'] = server_name
