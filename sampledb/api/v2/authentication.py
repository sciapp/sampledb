import typing
from collections.abc import Callable

import flask
from werkzeug.exceptions import HTTPException

from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from pydantic import BaseModel, Field

from ...logic.authentication import login, login_via_api_token, login_via_api_access_token, login_via_api_refresh_token, login_via_oidc_access_token, get_active_two_factor_authentication_methods, generate_api_access_token, refresh_api_access_token
from ...logic.users import User
from ...models import Permissions
from ...utils import object_permissions_required as object_permissions_required_generic, FlaskResponseT
from ..utils import Resource
from .utils.openapi import method
from ..errors import handle_api_error
from .utils.responses import BadRequestErrorModel


http_basic_auth = HTTPBasicAuth()
http_api_token_or_access_token_auth = HTTPTokenAuth(scheme='Bearer')
http_api_token_or_refresh_token_auth = HTTPTokenAuth(scheme='Bearer')
multi_auth = MultiAuth(http_basic_auth, http_api_token_or_access_token_auth)
multi_auth_for_access_tokens = MultiAuth(http_basic_auth, http_api_token_or_refresh_token_auth)


@http_api_token_or_access_token_auth.verify_token
def verify_api_token_or_access_token(api_token: str | None) -> User | None:
    if not api_token:
        return None

    # login_via_oidc_access_token should be the last method to be called,
    # otherwise, if OIDC is configured, even the login using other types of
    # API tokens would be blocked on an HTTP request.
    # Additionally, this avoids unnecessarily sharing valid API tokens with
    # the provider, even if the provider is trusted.
    user = login_via_api_token(api_token)
    if user is None:
        user = login_via_api_access_token(api_token)
    if user is None:
        user = login_via_oidc_access_token(api_token)

    if user is None or not user.is_active:
        return None
    flask.g.user = user
    return user


@http_api_token_or_refresh_token_auth.verify_token
def verify_api_token_or_refresh_token(api_token: str | None) -> User | None:
    if not api_token:
        return None
    user = login_via_api_token(api_token)
    if user is None:
        user = login_via_api_refresh_token(api_token)
        if user is not None:
            flask.g.api_refresh_token = api_token
    if user is None or not user.is_active:
        return None
    flask.g.user = user
    return user


@http_basic_auth.verify_password
def verify_password(username: str, password: str) -> User | None:
    if not username:
        return None
    user = login(username, password)
    if user is None or not user.is_active:
        return None
    two_factor_authentication_methods = get_active_two_factor_authentication_methods(user.id)
    if two_factor_authentication_methods:
        # two-factor authentication is not supported for the HTTP API
        return None
    flask.g.user = user
    return user


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


def object_permissions_required(permissions: Permissions) -> Callable[[typing.Any], typing.Any]:
    """
    Only allow access to a route it the user has the required permissions.

    Wrapper around the more generic sampledb.utils.object_permissions_required
    for use with the http_basic_auth object from this module.

    :param permissions: the required object permissions
    """
    return object_permissions_required_generic(
        required_object_permissions=permissions,
        auth_extension=multi_auth,
        user_id_callable=lambda: typing.cast(int, flask.g.user.id),
        may_enable_anonymous_users=False
    )


class AccessTokenModel(BaseModel):
    access_token: str = Field(..., title="Access Token", description="A token usable to authenticate with the API via HTTP Bearer authentication", examples=["be740310706c1050e7a1668e2c0c407e029559a862d544d2d059f363c9ad8219"])
    refresh_token: str = Field(..., title="Refresh Token", description="A token usable to authenticate with the /access_tokens/ endpoint via HTTP Bearer authentication to refresh an access token", examples=["a844185d4a924f52eec40d5b83f68fed8953665553b134dd5a02521250205b19"])
    expiration_utc_datetime: str = Field(..., title="Expiration Datetime", description="A string containing the datetime (in UTC) when the access token expires", examples=["2026-01-01 12:34:56"])
    description: str | None = Field(..., title="Description", description="Description of the access token", examples=["Access Token for Instrument Control"])


class AccessTokens(Resource):
    class RequestBodyModel(BaseModel):
        description: str = Field(..., title="Description", description="Description of the access token", examples=["Access Token for Instrument Control"])

    @multi_auth_for_access_tokens.login_required
    @method(default_status_code=201)
    def post(self, request_body: RequestBodyModel | None) -> BadRequestErrorModel | AccessTokenModel:
        """
        Create a new access token.
        """
        refresh_token = getattr(flask.g, 'api_refresh_token', None)
        if refresh_token:
            result = refresh_api_access_token(refresh_token)
            if result is None:
                return BadRequestErrorModel(
                    error="LogicError",
                    message="failed to refresh API token"
                )
            return AccessTokenModel(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                expiration_utc_datetime=result["expiration_utc_datetime"],
                description=result["description"]
            )
        if request_body is None:
            return BadRequestErrorModel(
                error="LogicError",
                message="neither description nor refresh API token provided"
            )
        access_token = generate_api_access_token(user_id=flask.g.user.id, description=request_body.description)
        return AccessTokenModel(
            access_token=typing.cast(str, access_token["access_token"]),
            refresh_token=typing.cast(str, access_token["refresh_token"]),
            expiration_utc_datetime=typing.cast(str, access_token["expiration_utc_datetime"]),
            description=access_token["description"]
        )
