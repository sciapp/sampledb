# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend

from ...logic.api_log import get_api_log_entries
from ...logic.authentication import Authentication, AuthenticationType

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/users/me/api_token_id/<int:api_token_id>/log/')
@flask_login.login_required
def current_user_api_log(api_token_id):
    return flask.redirect(flask.url_for('.api_log', user_id=flask_login.current_user.id, api_token_id=api_token_id))


@frontend.route('/users/<int:user_id>/api_token_id/<int:api_token_id>/log/')
@flask_login.login_required
def api_log(user_id, api_token_id):
    if user_id != flask_login.current_user.id and not flask_login.current_user.is_admin:
        return flask.abort(404)
    api_token = Authentication.query.filter_by(
        id=api_token_id,
        user_id=user_id,
        type=AuthenticationType.API_TOKEN
    ).first()
    if api_token is None:
        return flask.abort(404)
    api_log_entries = get_api_log_entries(api_token.id)
    return flask.render_template(
        'api_log.html',
        api_log_entries=api_log_entries,
        api_token_description=api_token.login.get('description', '-')
    )
