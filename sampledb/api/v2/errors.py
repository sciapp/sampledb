import flask
from werkzeug.exceptions import HTTPException

from .authentication import http_basic_auth, http_api_token_or_access_token_auth, http_api_token_or_refresh_token_auth
from ...utils import FlaskResponseT
from ..errors import handle_api_error


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
