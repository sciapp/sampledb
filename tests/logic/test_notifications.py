# coding: utf-8
"""

"""

import pytest
import sampledb
import sampledb.logic
import sampledb.models

from ..test_utils import flask_server, app, app_context


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
    sampledb.logic.notifications.create_other_notification(user.id, 'This is a test message')
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 1
    notification = sampledb.logic.notifications.get_notifications(user.id)[0]
    assert notification.type == sampledb.logic.notifications.NotificationType.OTHER
    assert notification.user_id == user.id
    assert not notification.was_read
    assert notification.data == {
        'message': 'This is a test message'
    }


def test_mark_notification_read(user):
    assert len(sampledb.logic.notifications.get_notifications(user.id)) == 0
    sampledb.logic.notifications.create_other_notification(user.id, 'This is a test message')
    assert len(sampledb.logic.notifications.get_notifications(user.id, True)) == 1
    notification = sampledb.logic.notifications.get_notifications(user.id)[0]
    assert not notification.was_read
    sampledb.logic.notifications.mark_notification_as_read(notification.id)
    assert len(sampledb.logic.notifications.get_notifications(user.id, True)) == 0
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
