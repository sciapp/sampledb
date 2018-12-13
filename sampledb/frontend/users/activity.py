# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend
from ...logic import user_log, users, errors, locations


@frontend.route('/users/me/activity')
@flask_login.login_required
def current_user_activity():
    return flask.redirect(flask.url_for('.user_activity', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>/activity')
@flask_login.login_required
def user_activity(user_id):
    try:
        user = users.get_user(user_id)
    except errors.UserDoesNotExistError:
        return flask.abort(404)
    user_log_entries = user_log.get_user_log_entries(user_id, as_user_id=flask_login.current_user.id)
    return flask.render_template('user_activity.html', user_log_entries=user_log_entries, UserLogEntryType=user_log.UserLogEntryType, user=user, get_object_location_assignment=locations.get_object_location_assignment)
