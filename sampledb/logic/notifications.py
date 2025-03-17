# coding: utf-8
"""

"""

import dataclasses
import datetime
import functools
import typing

import flask

from . import errors
from .. import logic
from ..models import notifications
from ..models.notifications import NotificationType, NotificationMode
from .background_tasks.send_mail import post_send_mail_task
from .. import db


@dataclasses.dataclass(frozen=True)
class Notification:
    """
    This class provides an immutable wrapper around models.notifications.Notification.
    """
    id: int
    type: NotificationType
    user_id: int
    data: typing.Dict[str, typing.Any]
    was_read: bool
    utc_datetime: typing.Optional[datetime.datetime] = None

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


def get_notifications(user_id: int, unread_only: bool = False, additional_filters: typing.Sequence[typing.Any] = ()) -> typing.List[Notification]:
    """
    Get all (unread) notifications for a given user.

    :param user_id: the ID of an existing user
    :param unread_only: whether only unread notifications should be returned
    :param additional_filters: additional filters for the notification query
    :return: a list of (unread) notifications
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure the user exists
    logic.users.check_user_exists(user_id)
    query = notifications.Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(was_read=False)
    for additional_filter in additional_filters:
        query = additional_filter(query)
    query = query.order_by(notifications.Notification.utc_datetime.desc())
    db_notifications = query.all()
    return [
        Notification.from_database(notification)
        for notification in db_notifications
    ]


def get_notifications_by_type(user_id: int, notification_type: NotificationType, unread_only: bool = False) -> typing.List[Notification]:
    """
    Get all (unread) notifications of a given type for a given user.

    :param user_id: the ID of an existing user
    :param notification_type: the type of notification to return
    :param unread_only: whether only unread notifications should be returned
    :return: a list of (unread) notifications
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    return get_notifications(
        user_id=user_id,
        unread_only=unread_only,
        additional_filters=[
            lambda query, notification_type=notification_type: query.filter_by(type=notification_type)
        ]
    )


def get_num_notifications(user_id: int, unread_only: bool = False) -> int:
    """
    Get the number of (unread) notifications for a given user.

    :param user_id: the ID of an existing user
    :param unread_only: whether only unread notifications should be returned
    :return: the number of (unread) notifications
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure the user exists
    logic.users.check_user_exists(user_id)
    num_notifications: int
    if unread_only:
        num_notifications = notifications.Notification.query.filter_by(user_id=user_id, was_read=False).count()
    else:
        num_notifications = notifications.Notification.query.filter_by(user_id=user_id).count()
    return num_notifications


def get_notification(notification_id: int) -> Notification:
    """
    Get a specific notification.

    :param notification_id: the ID of an existing notification
    :return: a notification
    :raise errors.NotificationDoesNotExistError: when no notification with the
        given notification ID exists
    """
    notification = notifications.Notification.query.filter_by(id=notification_id).first()
    if notification is None:
        raise errors.NotificationDoesNotExistError()
    return Notification.from_database(notification)


def _create_notification(type: NotificationType, user_id: int, data: typing.Dict[str, typing.Any]) -> None:
    """
    Create a new notification and handle it according to the user's settings.

    Use the convenience functions for creating specific notifications instead.

    :param type: the type of the new notification
    :param user_id: the ID of an existing user
    :param data: the data for the new notification
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    notification_mode = get_notification_mode_for_type(type, user_id)
    if notification_mode == NotificationMode.WEBAPP:
        _store_notification(type, user_id, data)
    if notification_mode == NotificationMode.EMAIL:
        _send_notification(type, user_id, data)


def _store_notification(type: NotificationType, user_id: int, data: typing.Dict[str, typing.Any]) -> None:
    """
    Store a new notification in the database.

    :param type: the type of the new notification
    :param user_id: the ID of an existing user
    :param data: the data for the new notification
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure the user exists
    logic.users.check_user_exists(user_id)
    notification = notifications.Notification(
        type=type,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(notification)
    db.session.commit()


def _send_notification(type: NotificationType, user_id: int, data: typing.Dict[str, typing.Any]) -> None:
    """
    Send a new notification by email.

    :param type: the type of the new notification
    :param user_id: the ID of an existing user
    :param data: the data for the new notification
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    user = logic.users.get_user(user_id)
    if user.email is None:
        return

    service_name = flask.current_app.config['SERVICE_NAME']
    subject = service_name + " Notification"

    template_path = 'mails/notifications/' + type.name.lower()

    html = flask.render_template(
        template_path + '.html',
        user=user,
        type=type,
        data=data,
        get_user=logic.users.get_user,
        get_group=logic.groups.get_group,
        get_project=logic.projects.get_project,
        get_instrument=logic.instruments.get_instrument,
        get_instrument_log_entry=logic.instrument_log_entries.get_instrument_log_entry,
        get_object_location_assignment=logic.locations.get_object_location_assignment,
        get_component=logic.components.get_component
    )
    text = flask.render_template(
        template_path + '.txt',
        user=user,
        type=type,
        data=data,
        get_user=logic.users.get_user,
        get_group=logic.groups.get_group,
        get_project=logic.projects.get_project,
        get_instrument=logic.instruments.get_instrument,
        get_instrument_log_entry=logic.instrument_log_entries.get_instrument_log_entry,
        get_object_location_assignment=logic.locations.get_object_location_assignment,
        get_component=logic.components.get_component
    )
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')

    post_send_mail_task(
        subject=subject,
        recipients=[user.email],
        text=text,
        html=html
    )


def mark_notification_as_read(notification_id: int) -> None:
    """
    Mark a notification as having been read.

    :param notification_id: the ID of an existing notification
    :raise errors.NotificationDoesNotExistError: when no notification with the
        given notification ID exists
    """
    notification = notifications.Notification.query.filter_by(id=notification_id).first()
    if notification is None:
        raise errors.NotificationDoesNotExistError()
    if not notification.was_read:
        notification.was_read = True
        db.session.add(notification)
        db.session.commit()


def mark_notification_for_being_assigned_as_responsible_user_as_read(user_id: int, object_location_assignment_id: int) -> None:
    """
    Mark notifications for an object location assignment as having been read.

    :param user_id: the ID of an existing user
    :param object_location_assignment_id: the object location assignment ID
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.NotificationDoesNotExistError: when no notification with the
        given notification ID exists
    """
    unread_notifications = get_notifications_by_type(
        user_id=user_id,
        notification_type=NotificationType.ASSIGNED_AS_RESPONSIBLE_USER,
        unread_only=True
    )
    for notification in unread_notifications:
        if notification.data.get('object_location_assignment_id', None) == object_location_assignment_id:
            mark_notification_as_read(notification.id)


def delete_notification(notification_id: int) -> None:
    """
    Delete a notification.

    :param notification_id: the ID of an existing notification
    :raise errors.NotificationDoesNotExistError: when no notification with the
        given notification ID exists
    """
    notification = notifications.Notification.query.filter_by(id=notification_id).first()
    if notification is None:
        raise errors.NotificationDoesNotExistError()
    db.session.delete(notification)
    db.session.commit()


def set_notification_mode_for_type(type: NotificationType, user_id: int, mode: NotificationMode) -> None:
    """
    Set the notification mode for a user for a specific notification type.

    :param type: the notification type to set the mode for
    :param user_id: the ID of an existing user
    :param mode: the notification mode to set for the type and user
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure the user exists
    logic.users.check_user_exists(user_id)
    notification_mode_for_type = notifications.NotificationModeForType.query.filter_by(type=type, user_id=user_id).first()
    if notification_mode_for_type is None:
        notification_mode_for_type = notifications.NotificationModeForType(type=type, user_id=user_id, mode=mode)
    else:
        notification_mode_for_type.mode = mode
    db.session.add(notification_mode_for_type)
    db.session.commit()


@functools.cache
def _get_default_notification_modes_impl(config_default_notification_modes_set: typing.FrozenSet[typing.Tuple[str, str]]) -> typing.Dict[NotificationType, NotificationMode]:
    config_default_notification_modes = dict(config_default_notification_modes_set)
    default_notification_modes = {}
    for notification_type in NotificationType:
        notification_mode = NotificationMode.WEBAPP
        for notification_type_key in (
            'DEFAULT',
            notification_type.name.upper()
        ):
            notification_mode_str = config_default_notification_modes.get(notification_type_key)
            if notification_mode_str:
                notification_mode = {
                    'WEBAPP': NotificationMode.WEBAPP,
                    'EMAIL': NotificationMode.EMAIL,
                    'IGNORE': NotificationMode.IGNORE,
                }[notification_mode_str]
        default_notification_modes[notification_type] = notification_mode
    return default_notification_modes


def get_default_notification_modes(config_default_notification_modes: typing.Optional[typing.Dict[str, str]]) -> typing.Dict[NotificationType, NotificationMode]:
    """
    Get the default notification modes.

    :param config_default_notification_modes: the default notification modes using strings from config
    :return: the default notification modes using internal types
    """
    if config_default_notification_modes is None:
        config_default_notification_modes = {}
    return dict(_get_default_notification_modes_impl(frozenset(config_default_notification_modes.items())))


def get_notification_mode_for_type(type: NotificationType, user_id: int) -> NotificationMode:
    """
    Get the notification mode for a user for a specific notification type.

    :param type: the notification type to get the mode for
    :param user_id: the ID of an existing user
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    user = logic.users.get_user(user_id)
    if user.component_id is not None:
        # disable notifications for users from other components
        return NotificationMode.IGNORE
    notification_mode_for_type = notifications.NotificationModeForType.query.filter_by(type=type, user_id=user_id).first()
    if notification_mode_for_type is not None:
        return notification_mode_for_type.mode
    default_notification_modes = get_default_notification_modes(flask.current_app.config['DEFAULT_NOTIFICATION_MODES'])
    return default_notification_modes[type]


def get_notification_modes(user_id: int) -> typing.Dict[NotificationType, NotificationMode]:
    """
    Get the notification modes for a user.

    :param user_id: the ID of an existing user
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure the user exists
    logic.users.check_user_exists(user_id)
    notification_modes = get_default_notification_modes(flask.current_app.config['DEFAULT_NOTIFICATION_MODES'])
    for notification_mode_for_type in notifications.NotificationModeForType.query.filter_by(user_id=user_id).all():
        notification_modes[notification_mode_for_type.type] = notification_mode_for_type.mode
    return notification_modes


def create_other_notification(user_id: int, message: str) -> None:
    """
    Create a notification of type OTHER.

    :param user_id: the ID of an existing user
    :param message: the message for the notification
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    _create_notification(
        type=NotificationType.OTHER,
        user_id=user_id,
        data={
            'message': message
        }
    )


def create_notification_for_being_assigned_as_responsible_user(object_location_assignment_id: int) -> None:
    """
    Create a notification of type ASSIGNED_AS_RESPONSIBLE_USER.

    :param object_location_assignment_id: the ID of an existing object location
        assignment
    :raise errors.ObjectLocationAssignmentDoesNotExistError: when no object
        location assignment with the given object location assignment ID exists
    """
    object_location_assignment = logic.locations.get_object_location_assignment(object_location_assignment_id)
    if object_location_assignment.responsible_user_id is None:
        return
    confirmation_url = flask.url_for(
        'frontend.accept_responsibility_for_object',
        t=logic.security_tokens.generate_token(
            object_location_assignment_id,
            salt='confirm_responsibility',
            secret_key=flask.current_app.config['SECRET_KEY']
        ),
        _external=True
    )
    declination_url = flask.url_for(
        'frontend.decline_responsibility_for_object',
        t=logic.security_tokens.generate_token(
            object_location_assignment_id,
            salt='decline_responsibility',
            secret_key=flask.current_app.config['SECRET_KEY']
        ),
        _external=True
    )
    _create_notification(
        type=NotificationType.ASSIGNED_AS_RESPONSIBLE_USER,
        user_id=object_location_assignment.responsible_user_id,
        data={
            'object_id': object_location_assignment.object_id,
            'assigner_id': object_location_assignment.user_id,
            'object_location_assignment_id': object_location_assignment_id,
            'confirmation_url': confirmation_url,
            'declination_url': declination_url
        }
    )


def create_notification_for_being_invited_to_a_group(
        user_id: int,
        group_id: int,
        inviter_id: int,
        confirmation_url: str,
        expiration_utc_datetime: typing.Optional[datetime.datetime],
        invitation_id: int
) -> None:
    """
    Create a notification of type INVITED_TO_GROUP.

    :param user_id: the ID of an existing user
    :param group_id: the ID of an existing group
    :param inviter_id: the ID of who invited this user to the group
    :param confirmation_url: the confirmation URL
    :param expiration_utc_datetime: the datetime when the confirmation URL expires (optional)
    :param invitation_id: the ID of an existing invitation
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        or assigner ID exists
    :raise errors.GroupDoesNotExistError: when no group with the given group
        ID exists
    """
    # ensure the group exists
    logic.groups.get_group(group_id)
    # ensure the inviter exists
    logic.users.check_user_exists(inviter_id)
    _create_notification(
        type=NotificationType.INVITED_TO_GROUP,
        user_id=user_id,
        data={
            'group_id': group_id,
            'inviter_id': inviter_id,
            'confirmation_url': confirmation_url,
            'expiration_utc_datetime': expiration_utc_datetime.strftime('%Y-%m-%d %H:%M:%S') if expiration_utc_datetime is not None else None,
            'invitation_id': invitation_id,
        }
    )


def create_notification_for_being_invited_to_a_project(
        user_id: int,
        project_id: int,
        inviter_id: int,
        confirmation_url: str,
        expiration_utc_datetime: typing.Optional[datetime.datetime],
        invitation_id: int
) -> None:
    """
    Create a notification of type INVITED_TO_PROJECT.

    :param user_id: the ID of an existing user
    :param project_id: the ID of an existing project
    :param inviter_id: the ID of who invited this user to the project
    :param confirmation_url: the confirmation URL
    :param expiration_utc_datetime: the datetime when the confirmation URL expires (optional)
    :param invitation_id: an ID of an existing invitation
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        or assigner ID exists
    :raise errors.ProjectDoesNotExistError: when no project with the given project
        ID exists
    """
    # ensure the project exists
    logic.projects.get_project(project_id)
    # ensure the inviter exists
    logic.users.check_user_exists(inviter_id)
    _create_notification(
        type=NotificationType.INVITED_TO_PROJECT,
        user_id=user_id,
        data={
            'project_id': project_id,
            'inviter_id': inviter_id,
            'confirmation_url': confirmation_url,
            'expiration_utc_datetime': expiration_utc_datetime.strftime('%Y-%m-%d %H:%M:%S') if expiration_utc_datetime is not None else None,
            'invitation_id': invitation_id
        }
    )


def create_announcement_notification(user_id: int, message: str, html: typing.Optional[str] = None) -> None:
    """
    Create a notification of type ANNOUNCEMENT.

    :param user_id: the ID of an existing user
    :param message: the message for the notification
    :param html: a HTML-formatted version of the message (optional)
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    _create_notification(
        type=NotificationType.ANNOUNCEMENT,
        user_id=user_id,
        data={
            'message': message,
            'html': html
        }
    )


def create_announcement_notification_for_all_users(message: str, html: typing.Optional[str] = None) -> None:
    """
    Create a notification of type ANNOUNCEMENT for all existing users.

    :param message: the message for the notification
    :param html: a HTML-formatted version of the message (optional)
    """
    for user in logic.users.get_users():
        create_announcement_notification(user.id, message, html)


def create_notification_for_having_received_an_objects_permissions_request(user_id: int, object_id: int, requester_id: int) -> None:
    """
    Create a notification of type RECEIVED_OBJECT_PERMISSIONS_REQUEST.

    :param user_id: the ID of an existing user
    :param object_id: the ID of an existing object
    :param requester_id: the ID of who requested permissions for this object
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        or requester ID exists
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    # ensure the object exists
    logic.objects.check_object_exists(object_id)
    # ensure the requester exists
    logic.users.check_user_exists(requester_id)
    _create_notification(
        type=NotificationType.RECEIVED_OBJECT_PERMISSIONS_REQUEST,
        user_id=user_id,
        data={
            'object_id': object_id,
            'requester_id': requester_id
        }
    )


def create_notification_for_a_new_instrument_log_entry(user_id: int, instrument_log_entry_id: int) -> None:
    """
    Create a notification of type INSTRUMENT_LOG_ENTRY_CREATED.

    :param user_id: the ID of an existing user
    :param instrument_log_entry_id: the ID of the instrument log entry
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.InstrumentLogEntryDoesNotExistError: when no instrument log
        entry with the given ID exists
    """
    # ensure the instrument log entry exists
    logic.instrument_log_entries.get_instrument_log_entry(instrument_log_entry_id)
    _create_notification(
        type=NotificationType.INSTRUMENT_LOG_ENTRY_CREATED,
        user_id=user_id,
        data={
            'instrument_log_entry_id': instrument_log_entry_id
        }
    )


def create_notification_for_being_referenced_by_object_metadata(user_id: int, object_id: int) -> None:
    """
    Create a notification of type REFERENCED_BY_OBJECT_METADATA.

    :param user_id: the ID of an existing user
    :param object_id: the ID of the object
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.ObjectDoesNotExistError: when no object with the given ID
        exists
    """
    # ensure the instrument log entry exists
    logic.objects.check_object_exists(object_id)
    _create_notification(
        type=NotificationType.REFERENCED_BY_OBJECT_METADATA,
        user_id=user_id,
        data={
            'object_id': object_id
        }
    )


def create_notification_for_an_edited_instrument_log_entry(
        user_id: int,
        instrument_log_entry_id: int,
        version_id: int
) -> None:
    """
    Create a notification of type INSTRUMENT_LOG_ENTRY_EDITED.

    :param user_id: the ID of an existing user
    :param instrument_log_entry_id: the ID of the instrument log entry
    :param version_id: the ID of the edited log entry version
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.InstrumentLogEntryDoesNotExistError: when no instrument log
        entry with the given ID exists
    """
    # ensure the instrument log entry exists
    logic.instrument_log_entries.get_instrument_log_entry(instrument_log_entry_id)
    _create_notification(
        type=NotificationType.INSTRUMENT_LOG_ENTRY_EDITED,
        user_id=user_id,
        data={
            'instrument_log_entry_id': instrument_log_entry_id,
            'version_id': version_id
        }
    )


def create_notification_for_a_declined_responsibility_assignment(
        user_id: int,
        object_location_assignment_id: int
) -> None:
    """
    Create a notification of type RESPONSIBILITY_ASSIGNMENT_DECLINED.

    :param user_id: the ID of an existing user
    :param object_location_assignment_id: the ID of an existing object location
        assignment
    :raise errors.ObjectLocationAssignmentDoesNotExistError: when no object
        location assignment with the given object location assignment ID exists
    """
    # ensure the object location assignment exists
    logic.locations.get_object_location_assignment(object_location_assignment_id)
    _create_notification(
        type=NotificationType.RESPONSIBILITY_ASSIGNMENT_DECLINED,
        user_id=user_id,
        data={
            'object_location_assignment_id': object_location_assignment_id,
        }
    )


def create_notification_for_a_failed_remote_object_import(
        user_id: int,
        object_id: int,
        component_id: int
) -> None:
    """
    Create a notification of type REMOTE_OBJECT_IMPORT_FAILED.

    :param user_id: the ID of an existing user
    :param object_id: the ID of an existing object
    :param component_id: the ID of an existing component
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.ComponentDoesNotExistError: when no component with the
        given component ID exists
    """
    # ensure the object exists
    logic.objects.check_object_exists(object_id)
    # ensure the component exists
    logic.components.check_component_exists(component_id)
    _create_notification(
        type=NotificationType.REMOTE_OBJECT_IMPORT_FAILED,
        user_id=user_id,
        data={
            'object_id': object_id,
            'component_id': component_id
        }
    )


def create_notification_for_a_remote_object_import_with_notes(
        user_id: int,
        object_id: int,
        component_id: int,
        import_notes: typing.List[str]
) -> None:
    """
    Create a notification of type REMOTE_OBJECT_IMPORT_NOTES.

    :param user_id: the ID of an existing user
    :param object_id: the ID of an existing object
    :param component_id: the ID of an existing component
    :param import_notes: the import notes from importing the object
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.ComponentDoesNotExistError: when no component with the
        given component ID exists
    """
    # ensure the object exists
    logic.objects.check_object_exists(object_id)
    # ensure the component exists
    logic.components.check_component_exists(component_id)
    _create_notification(
        type=NotificationType.REMOTE_OBJECT_IMPORT_NOTES,
        user_id=user_id,
        data={
            'object_id': object_id,
            'component_id': component_id,
            'import_notes': import_notes
        }
    )


def create_notification_for_being_automatically_linked(
    user_id: int,
    component_id: int,
    fed_id: int
) -> None:
    """
    Create a notification of type AUTOMATIC_USER_FEDERATION

    :param user_id: the ID of an existing user
    :param component_id: the ID of an existing component
    :param fed_id: the ID of the user on that component
    :raise errors.ComponentDoesNotExistError: when no component with the
        given component ID exists
    """
    # ensure the component exists
    logic.components.check_component_exists(component_id)
    _create_notification(
        type=NotificationType.AUTOMATIC_USER_FEDERATION,
        user_id=user_id,
        data={
            "user_id": fed_id,
            "component_id": component_id
        }
    )
