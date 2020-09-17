# coding: utf-8
"""

"""

import pytest
import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def user():
    user = sampledb.models.User(
        name="User",
        email="example1@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


def test_create_other_notification(user):
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 0
    assert sampledb.logic.notifications.get_num_notifications(user.id) == 0
    sampledb.logic.notifications.create_other_notification(user.id, 'This is a test message')
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 1
    assert sampledb.logic.notifications.get_num_notifications(user.id) == 1
    notification = sampledb.logic.notifications.get_notifications(user.id)[0]
    assert notification.type == sampledb.logic.notifications.NotificationType.OTHER
    assert notification.user_id == user.id
    assert not notification.was_read
    assert notification.data == {
        'message': 'This is a test message'
    }


def test_mark_notification_read(user):
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 0
    assert sampledb.logic.notifications.get_num_notifications(user.id) == 0
    sampledb.logic.notifications.create_other_notification(user.id, 'This is a test message')
    assert len(sampledb.logic.notifications.get_notifications(user.id, True)) == 1
    assert sampledb.logic.notifications.get_num_notifications(user.id, True) == 1
    notification = sampledb.logic.notifications.get_notifications(user.id)[0]
    assert not notification.was_read
    sampledb.logic.notifications.mark_notification_as_read(notification.id)
    assert len(sampledb.logic.notifications.get_notifications(user.id, True)) == 0
    assert sampledb.logic.notifications.get_num_notifications(user.id, True) == 0
    notification = sampledb.logic.notifications.get_notification(notification.id)
    assert notification.was_read

    with pytest.raises(sampledb.logic.errors.NotificationDoesNotExistError):
        sampledb.logic.notifications.mark_notification_as_read(notification.id + 1)


def test_delete_notification(user):
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 0
    sampledb.logic.notifications.create_other_notification(user.id, 'This is a test message')
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 1
    notification = sampledb.logic.notifications.get_notifications(user.id)[0]
    sampledb.logic.notifications.delete_notification(notification.id)
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 0

    with pytest.raises(sampledb.logic.errors.NotificationDoesNotExistError):
        sampledb.logic.notifications.mark_notification_as_read(notification.id)


def test_set_notification_mode(user):
    assert all(
        mode == sampledb.models.NotificationMode.WEBAPP
        for mode in sampledb.logic.notifications.get_notification_modes(user.id).values()
    )
    assert sampledb.logic.notifications.get_notification_mode_for_type(sampledb.models.NotificationType.OTHER, user.id) == sampledb.models.NotificationMode.WEBAPP
    sampledb.logic.notifications.set_notification_mode_for_type(sampledb.models.NotificationType.OTHER, user.id, sampledb.models.NotificationMode.EMAIL)
    assert all(
        mode == (sampledb.models.NotificationMode.EMAIL if type == sampledb.models.NotificationType.OTHER else sampledb.models.NotificationMode.WEBAPP)
        for type, mode in sampledb.logic.notifications.get_notification_modes(user.id).items()
    )
    sampledb.logic.notifications.set_notification_mode_for_type(sampledb.models.NotificationType.OTHER, user.id, sampledb.models.NotificationMode.IGNORE)
    assert sampledb.logic.notifications.get_notification_mode_for_type(sampledb.models.NotificationType.OTHER, user.id) == sampledb.models.NotificationMode.IGNORE
    sampledb.logic.notifications.set_notification_mode_for_all_types(user.id, sampledb.models.NotificationMode.EMAIL)
    assert all(
        mode == sampledb.models.NotificationMode.EMAIL
        for mode in sampledb.logic.notifications.get_notification_modes(user.id).values()
    )
    assert sampledb.logic.notifications.get_notification_mode_for_type(sampledb.models.NotificationType.OTHER, user.id) == sampledb.models.NotificationMode.EMAIL


def test_send_notification(app, user):
    sampledb.logic.notifications.set_notification_mode_for_all_types(user.id, sampledb.models.NotificationMode.EMAIL)
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 0

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.notifications.create_other_notification(user.id, 'This is a test message')

    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 0

    assert len(outbox) == 1
    assert 'example1@fz-juelich.de' in outbox[0].recipients
    message = outbox[0].html
    assert 'SampleDB Notification' in message
    assert 'This is a test message' in message
    app.config['SERVER_NAME'] = server_name


def test_create_announcement_notification(user):
    assert sampledb.logic.notifications.get_num_notifications(user.id) == 0
    sampledb.logic.notifications.create_announcement_notification_for_all_users('This is a test message', 'This is an html test message')
    assert sampledb.logic.notifications.get_num_notifications(user.id) == 1
    notification = sampledb.logic.notifications.get_notifications(user.id)[0]
    assert notification.type == sampledb.logic.notifications.NotificationType.ANNOUNCEMENT
    assert notification.user_id == user.id
    assert not notification.was_read
    assert notification.data == {
        'message': 'This is a test message',
        'html': 'This is an html test message'
    }
