# coding: utf-8
"""

"""

import typing
from time import time

import flask
import pytest
import requests_mock
from cryptojwt.jwk.rsa import new_rsa_key
from cryptojwt.jwt import JWT
from cryptojwt.key_jar import KeyJar
from furl import furl

import sampledb
import sampledb.logic
from sampledb.logic import oidc


@pytest.fixture
def setup():
    with requests_mock.Mocker() as m:
        m.get(
            "https://oidc_provider/.well-known/openid-configuration",
            json=OP_CONFIG,
            headers={"Content-Type": "application/json"},
        )
        m.get(
            "https://oidc_provider/certs",
            json=OP_KEYS,
        )

        flask.current_app.config["SERVER_NAME"] = "localhost"
        flask.current_app.config["OIDC_ISSUER"] = OP_CONFIG["issuer"]
        flask.current_app.config["OIDC_CLIENT_ID"] = "test_client"
        flask.current_app.config["OIDC_CLIENT_SECRET"] = "test_pw"

        with flask.current_app.app_context():
            oidc.init_app(flask.current_app)
            callback_url = flask.current_app.url_for(
                "frontend.oidc_callback",
                _external=True,
            )

        assert oidc._get_client().provider_config.issuer == OP_CONFIG["issuer"]

        yield m, callback_url, "https://localhost/some_path"


OP_CONFIG = {
    "issuer": "https://oidc_provider",
    "authorization_endpoint": "https://oidc_provider/auth",
    "token_endpoint": "https://oidc_provider/token",
    "introspection_endpoint": "https://oidc_provider/token/introspect",
    "userinfo_endpoint": "https://oidc_provider/userinfo",
    "end_session_endpoint": "https://oidc_provider/logout",
    "jwks_uri": "https://oidc_provider/certs",
    "grant_types_supported": ["authorization_code"],
    "response_types_supported": [
        "code",
        "id_token",
    ],
    "subject_types_supported": ["public"],
    "id_token_signing_alg_values_supported": ["RS256"],
    "response_modes_supported": [
        "query",
        "fragment",
    ],
    "token_endpoint_auth_methods_supported": ["client_secret_basic"],
    "claims_supported": [
        "aud",
        "sub",
        "iss",
        "auth_time",
        "name",
        "given_name",
        "family_name",
        "preferred_username",
        "email",
    ],
    "claim_types_supported": ["normal"],
    "claims_parameter_supported": True,
    "scopes_supported": ["email", "openid", "profile", "roles"],
    "code_challenge_methods_supported": ["plain", "S256"],
}

OP_KEY = new_rsa_key()

OP_KEYS = {
    "keys": [
        OP_KEY.serialize()
        | {
            "use": "sig",
            "alg": "RS256",
        }
    ]
}


def mk_jwt(**payload) -> str:
    jar = KeyJar()
    jar.add_keys(OP_CONFIG["issuer"], [OP_KEY])
    jwt = JWT(iss=OP_CONFIG["issuer"], key_jar=jar)
    return jwt.pack(
        payload=payload,
        issuer_id=OP_CONFIG["issuer"],
    )


def auth_helper(
    setup,
    sub: str = "123",
    email: str = "test@example.net",
    payload: dict = {},
    nonce_override: typing.Optional[str] = None,
):
    m, callback_url, next = setup
    auth_url, token = oidc.start_authentication(next)
    assert auth_url.startswith(OP_CONFIG["authorization_endpoint"])

    auth_furl = furl(auth_url)
    state = typing.cast(str, auth_furl.args["state"])
    nonce = typing.cast(str, auth_furl.args["nonce"])
    assert auth_furl.args["scope"] == flask.current_app.config["OIDC_SCOPES"]
    assert auth_furl.args["client_id"] == flask.current_app.config["OIDC_CLIENT_ID"]
    assert auth_furl.args["redirect_uri"] == callback_url

    code = "test_code"

    m.post(
        "https://oidc_provider/token",
        json={
            "access_token": "access_token",
            "token_type": "Bearer",
            "id_token": mk_jwt(
                iss=OP_CONFIG["issuer"],
                sub=sub,
                aud="test_client",
                exp=int(time() + 500),
                nonce=nonce_override or nonce,
                **payload,
            ),
        },
    )

    m.get(
        "https://oidc_provider/userinfo",
        json={
            "sub": sub,
            "name": "Test",
            "email": email,
            "email_verified": True,
        },
        headers={"Content-Type": "application/json"},
    )

    return oidc.handle_authentication(
        str(
            furl(callback_url).add(
                args={
                    "state": state,
                    "code": code,
                }
            )
        ),
        token
    )


def test_oidc(setup):
    user, returned_next = auth_helper(setup)
    assert returned_next == setup[2]
    assert user.name == "Test"
    assert user.email == "test@example.net"

    same_user = auth_helper(setup)[0]
    assert same_user.id == user.id
    assert same_user.name == user.name
    assert same_user.email == user.email


def test_oidc_attribute_update(setup):
    user = auth_helper(setup)[0]

    not_updated_user = auth_helper(
        setup,
        payload={
            'email': 'test@example.org',
            'name': 'test',
        },
    )[0]
    assert not_updated_user.id == user.id
    assert not_updated_user.name == user.name
    assert not_updated_user.email == user.email

    updated_user = auth_helper(
        setup,
        payload={
            'email': 'test@example.org',
            'email_verified': True,
            'name': 'test',
        },
    )[0]

    assert updated_user.id == user.id
    assert updated_user.name == 'test'
    assert updated_user.email == 'test@example.org'


def test_oidc_missing_attributes(setup):
    with pytest.raises(RuntimeError, match='Missing required attributes in userinfo'):
        auth_helper(setup, email='')


def test_oidc_unstable_sub(setup):
    auth_helper(setup)

    with pytest.raises(RuntimeError, match="Unstable subject identifier from issuer"):
        auth_helper(setup, sub="fail")


def test_oidc_nonce(setup):
    with pytest.raises(AssertionError):
        auth_helper(setup, nonce_override="fail")


def test_oidc_account_creation_disabled(setup):
    flask.current_app.config["OIDC_CREATE_ACCOUNT"] = "no"
    with pytest.raises(RuntimeError, match="Automatic account creation disabled."):
        auth_helper(setup)


def test_oidc_account_creation_deny_existing(setup):
    flask.current_app.config["OIDC_CREATE_ACCOUNT"] = "deny_existing"

    sampledb.logic.users.create_user(
        "Test",
        "test@example.net",
        sampledb.logic.users.UserType.PERSON,
    )
    with pytest.raises(RuntimeError, match="Automatic linking is disabled."):
        auth_helper(setup)

    auth_helper(setup, email="test@example.org")


def test_oidc_duplicate_email(setup):
    sampledb.logic.users.create_user(
        "Test",
        "test@example.net",
        sampledb.logic.users.UserType.PERSON,
    )
    sampledb.logic.users.create_user(
        "Test",
        "test@example.net",
        sampledb.logic.users.UserType.PERSON,
    )
    with pytest.raises(RuntimeError, match="Multiple matching accounts."):
        auth_helper(setup)


def test_oidc_duplicate_auth_method(setup):
    user1 = sampledb.logic.users.create_user(
        "Test",
        "test@example.net",
        sampledb.logic.users.UserType.PERSON,
    )
    sampledb.logic.authentication.add_oidc_authentication(
        user1.id,
        OP_CONFIG['issuer'],
        '123',
    )

    user2 = sampledb.logic.users.create_user(
        "Test",
        "test@example.net",
        sampledb.logic.users.UserType.PERSON,
    )
    sampledb.logic.authentication.add_oidc_authentication(
        user2.id,
        OP_CONFIG['issuer'],
        '123',
    )

    with pytest.raises(RuntimeError, match=r'More than one user with iss = ".+" and sub = ".+"'):
        auth_helper(setup)


def test_oidc_multiple_issuer(setup):
    user1 = sampledb.logic.users.create_user(
        "Test",
        "test@example.net",
        sampledb.logic.users.UserType.PERSON,
    )
    sampledb.logic.authentication.add_oidc_authentication(
        user1.id,
        'fail',
        'fail',
    )
    with pytest.raises(RuntimeError, match='OIDC authentication method from other issuer'):
        auth_helper(setup)


def test_oidc_roles(setup):
    flask.current_app.config["OIDC_ROLES"] = "resource_access.sampledb.1"

    user = auth_helper(
        setup,
        payload={
            "resource_access": {
                "sampledb": [
                    None,
                    ["is_active", "is_not_active", "is_admin"],
                ],
            }
        },
    )[0]
    assert user.name == "Test"
    assert user.email == "test@example.net"
    assert user.is_active == False
    assert user.is_admin == True
    assert user.is_hidden == False
    assert user.is_readonly == False

    updated_user = auth_helper(
        setup,
        payload={
            "resource_access": {
                "sampledb": [
                    None,
                    ["is_active", "is_not_admin"],
                ],
            }
        },
    )[0]
    assert updated_user.id == user.id
    assert updated_user.name == user.name
    assert updated_user.email == user.email
    assert updated_user.is_active == True
    assert updated_user.is_admin == False
    assert updated_user.is_hidden == False
    assert updated_user.is_readonly == False

    with pytest.raises(Exception):
        auth_helper(setup)
