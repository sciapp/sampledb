# coding: utf-8
"""

"""


import flask
import flask_login
from flask_wtf import FlaskForm

from wtforms.fields import IntegerField
from wtforms.validators import InputRequired

from .. import frontend
from ...logic import errors, users
from ...logic.notifications import get_notification, get_notifications, mark_notification_as_read, delete_notification, NotificationType


class DeleteAllNotificationsForm(FlaskForm):
    delete_all_notifications_up_to_id = IntegerField(validators=[InputRequired()])


class MarkAllNotificationsAsReadForm(FlaskForm):
    mark_all_notifications_as_read_up_to_id = IntegerField(validators=[InputRequired()])


class DeleteNotificationForm(FlaskForm):
    delete_notification = IntegerField(validators=[InputRequired()])


class MarkNotificationAsReadForm(FlaskForm):
    mark_notification_read = IntegerField(validators=[InputRequired()])


@frontend.route('/users/me/notifications')
@flask_login.login_required
def current_user_notifications():
    return flask.redirect(flask.url_for('.notifications', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>/notifications', methods=['GET', 'POST'])
@flask_login.login_required
def notifications(user_id):
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
        flask.flash('The notifications have been deleted.', 'success')
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
        flask.flash('The notifications have been marked as unread.', 'success')
        return flask.redirect(flask.url_for('.notifications', user_id=user_id))

    if delete_notification_form.validate_on_submit():
        notification_id = int(delete_notification_form.delete_notification.data)
        try:
            notification = get_notification(notification_id)
            if notification.user_id == flask_login.current_user.id:
                delete_notification(notification_id)
        except errors.NotificationDoesNotExistError:
            flask.flash('This notification does not exist.', 'error')
        else:
            flask.flash('The notification has been deleted.', 'success')
        return flask.redirect(flask.url_for('.notifications', user_id=user_id))

    if mark_notification_as_read_form.validate_on_submit():
        notification_id = int(mark_notification_as_read_form.mark_notification_read.data)
        try:
            notification = get_notification(notification_id)
            if notification.user_id == flask_login.current_user.id:
                mark_notification_as_read(notification_id)
        except errors.NotificationDoesNotExistError:
            flask.flash('This notification does not exist.', 'error')
        else:
            flask.flash('The notification has been marked as read.', 'success')
        return flask.redirect(flask.url_for('.notifications', user_id=user_id))

    notifications=get_notifications(user_id)
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
        get_user=users.get_user
    )
