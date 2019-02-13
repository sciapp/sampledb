# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend
from ...logic import users, errors


@frontend.route('/users/me')
@flask_login.login_required
def current_user_profile():
    return flask.redirect(flask.url_for('.user_profile', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>')
@flask_login.login_required
def user_profile(user_id):
    try:
        user = users.get_user(user_id)
    except errors.UserDoesNotExistError:
        return flask.abort(404)
    return flask.render_template(
        'profile.html',
        user=user
    )
