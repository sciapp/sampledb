import typing

import flask
from werkzeug.exceptions import HTTPException

from .authentication import http_basic_auth, http_api_token_or_access_token_auth, http_api_token_or_refresh_token_auth
from ...utils import FlaskResponseT


def is_api_error() -> bool:
    return flask.request.blueprint == 'api' or flask.request.blueprint is None and flask.request.path.startswith('/api/')


def handle_api_error(error: typing.Any) -> FlaskResponseT:
    return flask.jsonify({
        "message": getattr(error, 'description', "The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.")
    }), int(getattr(error, 'code', 500))


@http_basic_auth.error_handler
@http_api_token_or_access_token_auth.error_handler
@http_api_token_or_refresh_token_auth.error_handler
def auth_error(status: int) -> FlaskResponseT:
    try:
        flask.abort(status)
    except HTTPException as e:
        return handle_api_error(e)
    else:
        return handle_api_error(None)
