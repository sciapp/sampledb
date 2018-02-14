# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from .. import logic
from ..logic.security_tokens import verify_token


@frontend.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@flask_login.login_required
def project(project_id):
    if 'token' in flask.request.args:
        token = flask.request.args.get('token')
        user_id = verify_token(token, salt='invite_to_project', secret_key=flask.current_app.config['SECRET_KEY'])
        if user_id != flask_login.current_user.id:
            try:
                invited_user = logic.users.get_user(user_id)
                flask.flash('Please sign in as user "{}" to accept this invitation.'.format(invited_user.name), 'error')
            except logic.errors.UserDoesNotExistError:
                pass
            return flask.abort(403)
        logic.projects.add_user_to_project(project_id, user_id, logic.permissions.Permissions.READ)
    return flask.abort(404)
