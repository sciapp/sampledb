# coding: utf-8
"""
Implementation of OpenID Connect.
"""

import hashlib
import secrets
import time
import typing

import flask
import pydantic
from furl import furl
from simple_openid_connect.pkce import generate_pkce_pair
from simple_openid_connect.client import OpenidClient
from simple_openid_connect.data import (
    IdToken, JwtAccessToken, RpInitiatedLogoutRequest, TokenErrorResponse,
    TokenIntrospectionSuccessResponse, TokenSuccessResponse,
    UserinfoErrorResponse
)
from simple_openid_connect.exceptions import UnsupportedByProviderError

from ..config import OIDC_REQUIRED_CONFIG_KEYS
from ..models import AuthenticationType, UserType
from . import authentication, users


def is_oidc_configured() -> bool:
    """
    Check whether all required OIDC configuration values are set.

    :return: whether all values are set, False otherwise
    """
    return all(
        flask.current_app.config[key]
        for key in OIDC_REQUIRED_CONFIG_KEYS
    )


def is_oidc_only_auth_method() -> bool:
    """
    Check whether OIDC is configured and OIDC and api keys are the only
    permitted authentication method.

    :return: whether oidc is the only available auth method, False otherwise
    """
    return is_oidc_configured() and flask.current_app.config['OIDC_ONLY']


def init_app(app: flask.Flask) -> None:
    """
    Initialize OIDC client. Requires valid OIDC config and app or request
    context.
    """
    client = OpenidClient.from_issuer_url(
        app.config['OIDC_ISSUER'],
        app.url_for('frontend.oidc_callback', _external=True),
        app.config['OIDC_CLIENT_ID'],
        app.config['OIDC_CLIENT_SECRET'],
        app.config['OIDC_SCOPES'],
    )
    app.extensions['sampledb.logic.oidc.client'] = client
    app.extensions['sampledb.logic.oidc.data'] = {}


def _get_client() -> OpenidClient:
    return typing.cast(
        OpenidClient,
        flask.current_app.extensions['sampledb.logic.oidc.client']
    )


class _Data(pydantic.BaseModel):
    redirect_uri: str
    state: str
    nonce_value: str | None
    code_challenge_method: typing.Literal['S256'] | None
    code_verifier: str | None
    started: float = pydantic.Field(default_factory=time.time)


def start_authentication(redirect_uri: str) -> typing.Tuple[str, str]:
    """
    Start an OIDC authentication attempt.

    The caller must redirect to the returned url and store the returned opaque
    string token in the user session by setting it via a HttpOnly cookie. The
    token must be given as an argument to `handle_authentication` and removed
    from the user session.

    :param redirect_uri: Where the user should be redirected to after the
        authentication has been finished.
    :return: A tuple of the url and the token.
    """

    client = _get_client()

    state = secrets.token_urlsafe(32)

    if flask.current_app.config['OIDC_DISABLE_NONCE']:
        nonce_value = None
        nonce_hash = None
    else:
        nonce_value = secrets.token_urlsafe(32)
        nonce_hash = hashlib.sha256(nonce_value.encode()).hexdigest()

    code_challenge_method: typing.Optional[typing.Literal['S256']]
    if 'S256' in getattr(client.provider_config, 'code_challenge_methods_supported', []):
        code_challenge_method = 'S256'
        code_verifier, code_challenge = generate_pkce_pair()
    else:
        code_challenge_method = None
        code_verifier = None
        code_challenge = None

    url = client.authorization_code_flow.start_authentication(
        state=state,
        nonce=nonce_hash,
        code_challenge_method=code_challenge_method,
        code_challenge=code_challenge,
    )
    data = _Data(
        redirect_uri=redirect_uri,
        state=state,
        nonce_value=nonce_value,
        code_challenge_method=code_challenge_method,
        code_verifier=code_verifier,
    ).model_dump_json()
    return url, data


def handle_authentication(url: str, token: str) -> tuple[users.User, str, str]:
    """
    Handle an OIDC authentication callback.

    The caller must provide the entire callback URL and the token returned by
    `start_authentication`. The token must then be removed from the user
    session.

    The function will either return the user, the ID token, and the next URL,
    or raise an error. The ID token should be saved and passed to the logout
    function. The next URL is the address the user tried to visit before being
    asked to authenticate.

    :param url: The request url.
    :param token: The token returned by `start_authentication`.
    :return: A tuple of the user, the ID token, and the next URL.
    """

    current_url = furl(url)
    data = _Data.model_validate_json(token)

    if current_url.args['state'] != data.state:
        raise RuntimeError('Incorrect state value')

    # Make the timeout configurable if necessary.
    if data.started < time.time() - 10 * 60:
        raise RuntimeError('Request timed out')

    client = _get_client()

    token_response = client.authorization_code_flow.handle_authentication_result(
        url,
        state=data.state,
        code_verifier=data.code_verifier,
    )

    if isinstance(token_response, TokenErrorResponse):
        raise RuntimeError('Token Error')

    if data.nonce_value is not None:
        nonce = hashlib.sha256(data.nonce_value.encode()).hexdigest()
    else:
        nonce = None

    id_token = client.decode_id_token(
        token_response.id_token,
        nonce=nonce,
    )

    authentication_methods = authentication.get_oidc_authentications_by_sub(
        id_token.iss,
        id_token.sub,
    )

    if len(authentication_methods) > 1:
        raise RuntimeError(
            f'More than one user with iss = "{id_token.iss}" '
            f'and sub = "{id_token.sub}"'
        )

    if authentication_methods:
        user = users.get_user(authentication_methods[0].user_id)
    else:
        user = _handle_new_user(client, token_response, id_token)

    user = _update_user(
        user=user,
        id_token=id_token,
    )

    # Do not handle errors, see note in function.
    user = _handle_roles(user, id_token)

    return user, token_response.id_token, data.redirect_uri


def logout(id_token_hint: str, post_logout_redirect_uri: str) -> str:
    """
    Return the URL to initiate a logout request with the OIDC Provider. If the
    OP does not support RP-Initiated Logout, the returned URL will default to
    the `post_logout_redirect_uri`.

    In either case, the user will ultimately be redirected to the
    `post_logout_redirect_uri`, whether by the OP or by the caller of this
    function.

    :param id_token_hint: The ID token returned in the authentication.
    :param post_logout_redirect_uri: The URL to which the OP should redirect
        the user.
    :return: The next URL.
    """
    client = _get_client()
    try:
        return client.initiate_logout(RpInitiatedLogoutRequest(
            id_token_hint=id_token_hint,
            client_id=client.client_auth.client_id,
            post_logout_redirect_uri=post_logout_redirect_uri,
        ))
    except UnsupportedByProviderError:
        return post_logout_redirect_uri


def validate_access_token(access_token: str) -> typing.Tuple[authentication.AuthenticationMethod, users.User]:
    """
    Validate the access token and return the corresponding authentication
    method and user, or raise an error if it's not a valid token.

    This does not create or update user accounts, aside from the OIDC roles.
    Those will be updated and their omission will fail the validation.

    Depending on the access token, a network request may be necessary to
    validate the token. OIDC_ACCESS_TOKEN_ALLOW_INTROSPECTION can be used to
    permit or deny making that request.

    :param access_token: The Access Token.
    :return: A tuple of the authentication method and the user.
    """

    response = _validate_access_token(access_token)

    if not response.iss or not response.sub:
        raise RuntimeError('Missing iss or sub.')

    [authentication_method] = authentication.get_oidc_authentications_by_sub(
        response.iss,
        response.sub,
    )

    user = users.get_user(authentication_method.user_id)
    # Do not handle errors, see note in function.
    user = _handle_roles(user, response)

    return authentication_method, user


def _validate_access_token(access_token: str) -> typing.Union[JwtAccessToken, TokenIntrospectionSuccessResponse]:
    client = _get_client()

    # Try to parse the token as a JwtAccessToken. If it's a JWT, validate it
    # and return the result or bail out if the validation fails.
    # If it's not a JWT and the config permits token introspection, use the
    # Introspection Endpoint and return a valid response or bail out.
    try:
        token = JwtAccessToken.parse_jwt(access_token, client.provider_keys)
    except Exception:
        pass
    else:
        token.validate_extern(
            client.provider_config.issuer,
            client.client_auth.client_id,
        )
        return token

    if flask.current_app.config['OIDC_ACCESS_TOKEN_ALLOW_INTROSPECTION']:
        introspection_response = client.introspect_token(
            access_token,
            token_type_hint='access_token',
        )
        if isinstance(introspection_response, TokenIntrospectionSuccessResponse):
            return introspection_response
        raise RuntimeError('Introspection Endpoint returned an error')

    raise RuntimeError('Not a JWT and not allowed to use introspection')


def _update_user(user: users.User, id_token: IdToken) -> users.User:
    name = typing.cast(
        typing.Union[str, None],
        getattr(id_token, 'name', None),
    )
    email = typing.cast(
        typing.Union[str, None],
        getattr(id_token, 'email', None),
    )
    email_verified = typing.cast(
        typing.Union[bool, None],
        getattr(id_token, 'email_verified', None),
    )

    if (
        name is not None and
        flask.current_app.config['ENFORCE_SPLIT_NAMES'] and
        ', ' not in name[1:-1]
    ):
        name = user.name

    if (
            name is not None and
            email is not None and
            email_verified and
            (name != user.name or email != user.email)
    ):
        users.update_user(
            user.id,
            updating_user_id=None,
            name=name,
            email=email,
        )
        return users.get_user(user.id)

    return user


def _handle_new_user(client: OpenidClient, token_response: TokenSuccessResponse, id_token: IdToken) -> users.User:
    if flask.current_app.config['OIDC_CREATE_ACCOUNT'] == 'no':
        raise RuntimeError('Automatic account creation disabled.')

    userinfo = client.fetch_userinfo(token_response.access_token)

    if isinstance(userinfo, UserinfoErrorResponse):
        raise RuntimeError('Userinfo error')

    try:
        name = typing.cast(str, userinfo.name)  # type: ignore
        email = typing.cast(str, userinfo.email)  # type: ignore
        email_verified = typing.cast(
            str, userinfo.email_verified)  # type: ignore
        if not name or '@' not in email:
            raise RuntimeError()
    except Exception as e:
        raise RuntimeError('Missing required attributes in userinfo') from e

    if not email_verified:
        raise RuntimeError('Email not verified')

    matching_users = users.get_users_by_email(email)

    if len(matching_users) > 1:
        raise RuntimeError('Multiple matching accounts.')
    if len(matching_users) == 1:
        if flask.current_app.config['OIDC_CREATE_ACCOUNT'] == 'deny_existing':
            raise RuntimeError('Automatic linking is disabled.')

        authentication_methods = authentication.get_authentication_methods(
            matching_users[0].id,
            {AuthenticationType.OIDC}
        )
        if authentication_methods:
            if any(method.login['iss'] == id_token.iss for method in authentication_methods):
                raise RuntimeError('Unstable subject identifier from issuer')
            raise RuntimeError('OIDC authentication method from other issuer')

        user = matching_users[0]
    else:
        user = users.create_user(
            name=name,
            email=email,
            type=UserType.PERSON,
        )

    authentication.add_oidc_authentication(
        user.id,
        id_token.iss,
        id_token.sub,
    )

    return user


def _handle_roles(
        user: users.User,
        obj: typing.Union[IdToken, JwtAccessToken, TokenIntrospectionSuccessResponse],
) -> users.User:
    if not flask.current_app.config['OIDC_ROLES']:
        return user

    # Note: Intentionally fail on any error. It's probably a config error and
    # we do not want anyone to login with incorrect permissions.

    i = obj.model_dump()
    for path in flask.current_app.config['OIDC_ROLES'].split('.'):
        if isinstance(i, list):
            path = int(path)
        i = i[path]  # pyright: ignore
    roles = typing.cast(list[str], i)

    def f(prop: str, func: typing.Callable[[int, bool], None]) -> bool:
        v = None
        if f'is_{prop}' in roles:
            v = True
        if f'is_not_{prop}' in roles:
            v = False
        if v is not None and v != getattr(user, f'is_{prop}'):
            func(user.id, v)
            return True
        return False

    refresh = False
    refresh |= f('active', users.set_user_active)
    refresh |= f('hidden', users.set_user_hidden)
    refresh |= f('readonly', users.set_user_readonly)
    refresh |= f('admin', users.set_user_administrator)
    if refresh:
        user = users.get_user(user.id)
    return user
