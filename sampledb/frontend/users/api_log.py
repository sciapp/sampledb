# coding: utf-8
"""

"""

import flask
import flask_login
from flask_babel import gettext

from .. import frontend
from ...logic import errors
from ...logic.authentication import get_authentication_method
from ...logic.api_log import get_api_log_entries
from ...models import AuthenticationType
from ...utils import FlaskResponseT

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/users/me/api_token_id/<int:api_token_id>/log/')
@flask_login.login_required
def current_user_api_log(api_token_id: int) -> FlaskResponseT:
    return flask.redirect(flask.url_for('.api_log', user_id=flask_login.current_user.id, api_token_id=api_token_id))


@frontend.route('/users/<int:user_id>/api_token_id/<int:api_token_id>/log/')
@flask_login.login_required
def api_log(user_id: int, api_token_id: int) -> FlaskResponseT:
    if user_id != flask_login.current_user.id and not flask_login.current_user.is_admin:
        return flask.abort(404)
    try:
        api_token = get_authentication_method(authentication_method_id=api_token_id)
    except errors.AuthenticationMethodDoesNotExistError:
        return flask.abort(404)
    if api_token.user_id != user_id or api_token.type not in {AuthenticationType.API_TOKEN, AuthenticationType.API_ACCESS_TOKEN}:
        return flask.abort(404)
    api_log_entries = get_api_log_entries(api_token.id)
    if api_token.type == AuthenticationType.API_TOKEN:
        api_token_type = gettext('API token')
    else:
        api_token_type = gettext('API access token')
    return flask.render_template(
        'api_log.html',
        api_log_entries=api_log_entries,
        api_token_type=api_token_type,
        api_token_description=api_token.login.get('description', '-')
    )
