# coding: utf-8
"""

"""

import collections
import datetime
import typing
from . import errors, users, objects
from ..models import notifications
from ..models.notifications import NotificationType
from .. import db


class Notification(collections.namedtuple('Notification', ['id', 'type', 'user_id', 'data', 'was_read', 'utc_datetime'])):
    """
    This class provides an immutable wrapper around models.notifications.Notification.
    """

    def __new__(cls, id: int, type: NotificationType, user_id: int, data: typing.Dict[str, typing.Any], was_read: bool, utc_datetime: typing.Optional[datetime.datetime]=None):
        self = super(Notification, cls).__new__(cls, id, type, user_id, data, was_read, utc_datetime)
        return self

    @classmethod
    def from_database(cls, notification: notifications.Notification) -> 'Notification':
        return Notification(
            id=notification.id,
            type=notification.type,
            user_id=notification.user_id,
            data=notification.data,
            was_read=notification.was_read,
            utc_datetime=notification.utc_datetime
        )


def get_notifications(user_id: int, unread_only: bool=False) -> typing.List[Notification]:
    """
    Get all (unread) notifications for a given user.

    :param user_id: the ID of an existing user
    :param unread_only: whether only unread notifications should be returned
    :return: a list of (unread) notifications
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure the user exists
    users.get_user(user_id)
    if unread_only:
        db_notifications = notifications.Notification.query.filter_by(user_id=user_id, was_read=False).order_by(notifications.Notification.utc_datetime.desc()).all()
    else:
        db_notifications = notifications.Notification.query.filter_by(user_id=user_id).order_by(notifications.Notification.utc_datetime.desc()).all()
    return [
        Notification.from_database(notification)
        for notification in db_notifications
    ]


def get_num_notifications(user_id: int, unread_only: bool=False) -> int:
    """
    Get the number of (unread) notifications for a given user.

    :param user_id: the ID of an existing user
    :param unread_only: whether only unread notifications should be returned
    :return: the number of (unread) notifications
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure the user exists
    users.get_user(user_id)
    if unread_only:
        return notifications.Notification.query.filter_by(user_id=user_id, was_read=False).count()
    else:
        return notifications.Notification.query.filter_by(user_id=user_id).count()


def get_notification(notification_id) -> Notification:
    """
    Get a specific notification.

    :param notification_id: the ID of an existing notification
    :return: a notification
    :raise errors.NotificationDoesNotExist: when no notification with the
        given notification ID exists
    """
    notification = notifications.Notification.query.filter_by(id=notification_id).first()
    if notification is None:
        raise errors.NotificationDoesNotExistError()
    return Notification.from_database(notification)


def _store_notification(type: NotificationType, user_id: int, data: typing.Dict[str, typing.Any]) -> None:
    """
    Store a new notification in the database.

    Use the convenience functions for creating specific notifications instead.

    :param type: the type of the new notification
    :param user_id: the ID of an existing user
    :param data: the data for the new notification
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure the user exists
    users.get_user(user_id)
    notification = notifications.Notification(
        type=type,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.utcnow()
    )
    db.session.add(notification)
    db.session.commit()


def mark_notification_as_read(notification_id: int) -> None:
    """
    Mark a notification as having been read.

    :param notification_id: the ID of an existing notification
    :raise errors.NotificationDoesNotExist: when no notification with the
        given notification ID exists
    """
    notification = notifications.Notification.query.filter_by(id=notification_id).first()
    if notification is None:
        raise errors.NotificationDoesNotExistError()
    if not notification.was_read:
        notification.was_read = True
        db.session.add(notification)
        db.session.commit()


def delete_notification(notification_id: int) -> None:
    """
    Delete a notification.

    :param notification_id: the ID of an existing notification
    :raise errors.NotificationDoesNotExist: when no notification with the
        given notification ID exists
    """
    notification = notifications.Notification.query.filter_by(id=notification_id).first()
    if notification is None:
        raise errors.NotificationDoesNotExistError()
    db.session.delete(notification)
    db.session.commit()


def create_other_notification(user_id: int, message: str) -> None:
    """
    Create a notification of type OTHER.

    :param user_id: the ID of an existing user
    :param message: the message for the notification
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    _store_notification(
        type=NotificationType.OTHER,
        user_id=user_id,
        data={
            'message': message
        }
    )


def create_notification_for_being_assigned_as_responsible_user(user_id: int, object_id: int, assigner_id: int) -> None:
    """
    Create a notification of type ASSIGNED_AS_RESPONSIBLE_USER.

    :param user_id: the ID of an existing user
    :param object_id: the ID of an existing object
    :param assigner_id: the ID of who assigned this user as responsible user
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        or assigner ID exists
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    # ensure the object exists
    objects.get_object(object_id)
    # ensure the assigner exists
    users.get_user(assigner_id)
    _store_notification(
        type=NotificationType.ASSIGNED_AS_RESPONSIBLE_USER,
        user_id=user_id,
        data={
            'object_id': object_id,
            'assigner_id': assigner_id
        }
    )
