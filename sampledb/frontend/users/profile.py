# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend


@frontend.route('/users/me')
@flask_login.login_required
def current_user_profile():
    return flask.redirect(flask.url_for('.user_profile', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>')
@flask_login.login_required
def user_profile(user_id):
    # TODO: this is a placeholder for now. user profiles will be implemented in the future.
    return flask.redirect(flask.url_for('.index'))
