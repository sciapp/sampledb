# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend


@frontend.route('/users/me/activity')
@flask_login.login_required
def current_user_activity():
    return flask.redirect(flask.url_for('.user_profile', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>/activity')
@flask_login.login_required
def user_activity(user_id):
    return flask.redirect(flask.url_for('.user_profile', user_id=user_id))
