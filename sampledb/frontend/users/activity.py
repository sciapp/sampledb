# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend
from ...logic import user_log


@frontend.route('/users/me/activity')
@flask_login.login_required
def current_user_activity():
    return flask.redirect(flask.url_for('.user_activity', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>/activity')
@flask_login.login_required
def user_activity(user_id):
    if user_id != flask_login.current_user.id and not flask_login.current_user.is_admin:
        return flask.abort(403)
    user_log_entries = user_log.get_user_log_entries(user_id)
    return flask.render_template('user_activity.html', user_log_entries=user_log_entries, UserLogEntryType=user_log.UserLogEntryType)
