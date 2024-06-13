# coding: utf-8
"""

"""

import datetime
import typing

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm

from wtforms.fields import IntegerField
from wtforms.validators import InputRequired

from .. import frontend
from ...logic import errors, users, groups, projects, object_permissions, locations, instrument_log_entries, instruments, components
from ...logic.notifications import get_notification, get_notifications, mark_notification_as_read, delete_notification
from ...models import NotificationType, Permissions
from ...utils import FlaskResponseT


class DeleteAllNotificationsForm(FlaskForm):
    delete_all_notifications_up_to_id = IntegerField(validators=[InputRequired()])


class MarkAllNotificationsAsReadForm(FlaskForm):
    mark_all_notifications_as_read_up_to_id = IntegerField(validators=[InputRequired()])


class DeleteNotificationForm(FlaskForm):
    delete_notification = IntegerField(validators=[InputRequired()])


class MarkNotificationAsReadForm(FlaskForm):
    mark_notification_read = IntegerField(validators=[InputRequired()])


def _object_location_assignment_is_confirmed_or_declined(object_location_assignment_id: int) -> bool:
    try:
        object_location_assignment = locations.get_object_location_assignment(object_location_assignment_id)
    except errors.ObjectLocationAssignmentDoesNotExistError:
        return False
    return bool(object_location_assignment.confirmed or object_location_assignment.declined)


@frontend.route('/users/me/notifications')
@flask_login.login_required
def current_user_notifications() -> FlaskResponseT:
    return flask.redirect(flask.url_for('.notifications', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>/notifications', methods=['GET', 'POST'])
@flask_login.login_required
def notifications(user_id: int) -> FlaskResponseT:
    if user_id != flask_login.current_user.id:
        return flask.abort(403)

    delete_all_notifications_form = DeleteAllNotificationsForm()
    mark_all_notifications_as_read_form = MarkAllNotificationsAsReadForm()
    delete_notification_form = DeleteNotificationForm()
    mark_notification_as_read_form = MarkNotificationAsReadForm()

    if delete_all_notifications_form.validate_on_submit():
        max_known_notification_id = int(delete_all_notifications_form.delete_all_notifications_up_to_id.data)
        notifications = get_notifications(user_id)
        for notification in notifications:
            if notification.id <= max_known_notification_id:
                try:
                    delete_notification(notification.id)
                except errors.NotificationDoesNotExistError:
                    continue
        flask.flash(_('The notifications have been deleted.'), 'success')
        return flask.redirect(flask.url_for('.notifications', user_id=user_id))

    if mark_all_notifications_as_read_form.validate_on_submit():
        max_known_notification_id = int(mark_all_notifications_as_read_form.mark_all_notifications_as_read_up_to_id.data)
        notifications = get_notifications(user_id, unread_only=True)
        for notification in notifications:
            if notification.id <= max_known_notification_id:
                try:
                    mark_notification_as_read(notification.id)
                except errors.NotificationDoesNotExistError:
                    continue
        flask.flash(_('The notifications have been marked as read.'), 'success')
        return flask.redirect(flask.url_for('.notifications', user_id=user_id))

    if delete_notification_form.validate_on_submit():
        notification_id = int(delete_notification_form.delete_notification.data)
        try:
            notification = get_notification(notification_id)
            if notification.user_id == flask_login.current_user.id:
                delete_notification(notification_id)
        except errors.NotificationDoesNotExistError:
            flask.flash(_('This notification does not exist.'), 'error')
        else:
            flask.flash(_('The notification has been deleted.'), 'success')
        return flask.redirect(flask.url_for('.notifications', user_id=user_id))

    if mark_notification_as_read_form.validate_on_submit():
        notification_id = int(mark_notification_as_read_form.mark_notification_read.data)
        try:
            notification = get_notification(notification_id)
            if notification.user_id == flask_login.current_user.id:
                mark_notification_as_read(notification_id)
        except errors.NotificationDoesNotExistError:
            flask.flash(_('This notification does not exist.'), 'error')
        else:
            flask.flash(_('The notification has been marked as read.'), 'success')
        return flask.redirect(flask.url_for('.notifications', user_id=user_id))

    notifications = get_notifications(user_id)
    if notifications:
        max_known_notification_id = max(notification.id for notification in notifications)
    else:
        max_known_notification_id = 0
    return flask.render_template(
        'notifications.html',
        NotificationType=NotificationType,
        notifications=notifications,
        max_known_notification_id=max_known_notification_id,
        delete_all_notifications_form=delete_all_notifications_form,
        mark_all_notifications_as_read_form=mark_all_notifications_as_read_form,
        delete_notification_form=delete_notification_form,
        mark_notification_as_read_form=mark_notification_as_read_form,
        get_user=users.get_user,
        get_group=_safe_get_group,
        is_group_member=_is_group_member,
        get_project=_safe_get_project,
        is_group_invitation_revoked=_is_group_invitation_revoked,
        is_project_invitation_revoked=_is_project_invitation_revoked,
        get_instrument=_safe_get_instrument,
        get_instrument_log_entry=_safe_get_instrument_log_entry,
        get_component=components.get_component,
        is_project_member=_is_project_member,
        get_user_object_permissions=object_permissions.get_user_object_permissions,
        get_object_location_assignment=_safe_get_object_location_assignment,
        Permissions=Permissions,
        object_location_assignment_is_confirmed_or_declined=_object_location_assignment_is_confirmed_or_declined,
        datetime=datetime
    )


def _safe_get_object_location_assignment(
        object_location_assignment_id: int
) -> typing.Optional[locations.ObjectLocationAssignment]:
    try:
        return locations.get_object_location_assignment(object_location_assignment_id)
    except errors.ObjectLocationAssignmentDoesNotExistError:
        return None


def _safe_get_group(group_id: int) -> typing.Optional[groups.Group]:
    try:
        return groups.get_group(group_id)
    except errors.GroupDoesNotExistError:
        return None


def _is_group_member(user_id: int, group_id: int) -> bool:
    user_groups = groups.get_user_groups(user_id)
    if not user_groups:
        return False
    return any(group_id == group.id for group in user_groups)


def _safe_get_project(project_id: int) -> typing.Optional[projects.Project]:
    try:
        return projects.get_project(project_id)
    except errors.ProjectDoesNotExistError:
        return None


def _is_project_member(user_id: int, project_id: int) -> bool:
    user_projects = projects.get_user_projects(user_id)
    if not user_projects:
        return False
    return any(project_id == project.id for project in user_projects)


def _safe_get_instrument(instrument_id: int) -> typing.Optional[instruments.Instrument]:
    try:
        return instruments.get_instrument(instrument_id)
    except errors.InstrumentDoesNotExistError:
        return None


def _safe_get_instrument_log_entry(instrument_log_entry_id: int) -> typing.Optional[instrument_log_entries.InstrumentLogEntry]:
    try:
        return instrument_log_entries.get_instrument_log_entry(instrument_log_entry_id)
    except errors.InstrumentLogEntryDoesNotExistError:
        return None


def _is_group_invitation_revoked(invitation_id: typing.Optional[int]) -> bool:
    if invitation_id is None:
        return False
    return groups.get_group_invitation(invitation_id).revoked


def _is_project_invitation_revoked(invitation_id: typing.Optional[int]) -> bool:
    if invitation_id is None:
        return False
    return projects.get_project_invitation(invitation_id).revoked
