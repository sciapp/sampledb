# coding: utf-8
"""
Authentication functions for the SampleDB RESTful API.
"""
import typing

import flask

from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth

from ...logic.authentication import login, login_via_api_token, login_via_api_access_token, login_via_api_refresh_token, login_via_oidc_access_token, get_active_two_factor_authentication_methods, generate_api_access_token, refresh_api_access_token
from ...logic.users import User
from ...models import Permissions
from ...utils import object_permissions_required as object_permissions_required_generic
from ..utils import Resource, ResponseData

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

http_basic_auth = HTTPBasicAuth()
http_api_token_or_access_token_auth = HTTPTokenAuth(scheme='Bearer')
http_api_token_or_refresh_token_auth = HTTPTokenAuth(scheme='Bearer')
multi_auth = MultiAuth(http_basic_auth, http_api_token_or_access_token_auth)
multi_auth_for_access_tokens = MultiAuth(http_basic_auth, http_api_token_or_refresh_token_auth)


@http_api_token_or_access_token_auth.verify_token
def verify_api_token_or_access_token(api_token: typing.Optional[str]) -> typing.Optional[User]:
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
def verify_api_token_or_refresh_token(api_token: typing.Optional[str]) -> typing.Optional[User]:
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
def verify_password(username: str, password: str) -> typing.Optional[User]:
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


def object_permissions_required(permissions: Permissions) -> typing.Callable[[typing.Any], typing.Any]:
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


class AccessTokens(Resource):
    @multi_auth_for_access_tokens.login_required
    def post(self) -> ResponseData:
        refresh_token = getattr(flask.g, 'api_refresh_token', None)
        if refresh_token:
            result = refresh_api_access_token(refresh_token)
            if result is None:
                return {
                    "message": "failed to refresh API token"
                }, 400
            return result, 201
        request_json = flask.request.get_json(force=True, silent=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON body should contain object"
            }, 400
        if set(request_json.keys()) != {'description'}:
            return {
                "message": "JSON body should only contain description"
            }, 400
        description = request_json.get('description')
        if not isinstance(description, str):
            return {
                "message": "description must be a string"
            }, 400
        return generate_api_access_token(user_id=flask.g.user.id, description=description), 201
