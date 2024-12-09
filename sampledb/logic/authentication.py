import base64
import datetime
import functools
import secrets
import typing
import urllib.parse

import bcrypt
import flask
import fido2.features
from fido2.server import Fido2Server
from fido2.webauthn import AttestationConveyancePreference, PublicKeyCredentialRpEntity, AttestedCredentialData

from .. import logic, db
from .ldap import validate_user, create_user_from_ldap, is_ldap_configured
from ..models import Authentication, AuthenticationType, TwoFactorAuthenticationMethod, HTTPMethod
from . import errors, api_log

# enable JSON mapping for webauthn options
fido2.features.webauthn_json_mapping.enabled = True


# number of rounds for generating new salts for hashing passwords with crypt
# 12 is the default in the Python bcrypt module, this variable allows
# overriding this in tests
NUM_BCYRPT_ROUNDS = 12


def _hash_password(password: str) -> str:
    return str(bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=NUM_BCYRPT_ROUNDS)).decode('utf-8'))


def _validate_password_hash(password: str, password_hash: str) -> bool:
    return bool(bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')))


def _validate_password_authentication(authentication_method: Authentication, password: str) -> bool:
    password_hash = authentication_method.login['bcrypt_hash']
    return _validate_password_hash(password, password_hash)


def _add_password_authentication(user_id: int, login: str, password: str, authentication_type: AuthenticationType, confirmed: bool = True) -> None:
    login = login.lower().strip()
    if Authentication.query.filter(Authentication.login['login'].astext == login).first():
        raise errors.AuthenticationMethodAlreadyExists('An authentication method with this login already exists')
    authentication = Authentication(
        login={'login': login, 'bcrypt_hash': _hash_password(password)},
        authentication_type=authentication_type,
        confirmed=confirmed,
        user_id=user_id
    )
    db.session.add(authentication)
    db.session.commit()


def add_other_authentication(user_id: int, name: str, password: str, confirmed: bool = True) -> None:
    """
    Add an authentication method of type OTHER for a given user.

    :param user_id: the ID of an existing user
    :param name: the name to use during authentication
    :param password: the password
    :param confirmed: whether the authentication method has been confirmed already
    """
    _add_password_authentication(user_id, name, password, AuthenticationType.OTHER, confirmed)


def add_email_authentication(user_id: int, email: str, password: str, confirmed: bool = True) -> None:
    """
    Add an authentication method of type EMAIL for a given user.

    :param user_id: the ID of an existing user
    :param email: the email to use during authentication
    :param password: the password
    :param confirmed: whether the authentication method has been confirmed already
    :raise errors.AuthenticationMethodWrong: when email is no valid email
        address
    """
    email = email.lower().strip()
    if '@' not in email[1:-1]:
        raise errors.AuthenticationMethodWrong('Login must be a valid email address')
    _add_password_authentication(user_id, email, password, AuthenticationType.EMAIL, confirmed)
    if not confirmed:
        logic.utils.send_email_confirmation_email(
            email=email,
            user_id=user_id,
            salt='add_login'
        )


def add_ldap_authentication(user_id: int, ldap_uid: str, password: str, confirmed: bool = True) -> None:
    """
    Add an authentication method of type LDAP for a given user.

    :param user_id: the ID of an existing user
    :param ldap_uid: the LDAP uid to use during authentication
    :param password: the LDAP password
    :param confirmed: whether the authentication method has been confirmed already
    :raise errors.AuthenticationMethodAlreadyExists: when an LDAP authentication
        method with the given UID already exists
    :raise errors.LDAPAccountAlreadyExistError: when an LDAP authentication
        method already exists for this user
    :raise errors.LDAPAccountOrPasswordWrongError: when the UID and password
        combination could not be validated
    """
    ldap_uid = ldap_uid.lower().strip()
    if Authentication.query.filter(Authentication.login['login'].astext == ldap_uid).first():
        raise errors.AuthenticationMethodAlreadyExists('An authentication method with this login already exists')
    if Authentication.query.filter(Authentication.type == AuthenticationType.LDAP, Authentication.user_id == user_id).first():
        raise errors.LDAPAccountAlreadyExistError('An LDAP-based authentication method already exists for this user')
    if not validate_user(ldap_uid, password):
        raise errors.LDAPAccountOrPasswordWrongError('Ldap login or password wrong')
    authentication = Authentication(
        login={'login': ldap_uid},
        authentication_type=AuthenticationType.LDAP,
        confirmed=confirmed,
        user_id=user_id
    )
    db.session.add(authentication)
    db.session.commit()


def add_api_token(user_id: int, api_token: str, description: str) -> None:
    """
    Add an API token as an authentication method for a given user.

    :param user_id: the ID of an existing user
    :param api_token: the api token as a 64 character string
    :param description: a description for the token
    """

    assert len(api_token) == 64
    api_token = api_token.lower()
    # split into a short part (8 hex digits / 4 bytes) for identification and a long part for authentication
    login, password = api_token[:8], api_token[8:]
    authentication = Authentication(
        login={
            'login': login,
            'bcrypt_hash': _hash_password(password),
            'description': description
        },
        authentication_type=AuthenticationType.API_TOKEN,
        confirmed=True,
        user_id=user_id
    )
    db.session.add(authentication)
    db.session.commit()


def get_api_tokens(user_id: int) -> typing.Sequence[Authentication]:
    """
    Get all API tokens for a given user.

    :param user_id: the ID of an existing user
    :return: the API tokens for the user
    """
    return Authentication.query.filter_by(user_id=user_id, type=AuthenticationType.API_TOKEN).all()


def add_fido2_passkey(user_id: int, credential_data: AttestedCredentialData, description: str) -> None:
    """
    Add a FIDO2 passkey as an authentication method for a given user.

    :param user_id: the ID of an existing user
    :param credential_data: the passkey credential data
    :param description: a description for the passkey
    """
    authentication = Authentication(
        login={
            'credential_id': base64.b64encode(credential_data.credential_id).decode('utf-8'),
            'credential_data': base64.b64encode(credential_data).decode('utf-8'),
            'description': description
        },
        authentication_type=AuthenticationType.FIDO2_PASSKEY,
        confirmed=True,
        user_id=user_id
    )
    db.session.add(authentication)
    db.session.commit()


def get_all_fido2_passkey_credentials() -> typing.Sequence[AttestedCredentialData]:
    """
    Get all known FIDO2 passkey credentials.

    :return: a list of credentials
    """
    return [
        AttestedCredentialData(base64.b64decode(authentication.login['credential_data'].encode('utf-8')))
        for authentication in Authentication.query.filter_by(type=AuthenticationType.FIDO2_PASSKEY).all()
    ]


def get_user_id_for_fido2_passkey_credential_id(credential_id: bytes) -> typing.Optional[int]:
    """
    Get the user ID for a given FIDO2 passkey credential ID.

    :return: the user ID, or None if the credential ID is unknown
    """
    authentication = Authentication.query.filter(
        db.and_(
            Authentication.type == AuthenticationType.FIDO2_PASSKEY,
            Authentication.login['credential_id'].astext == base64.b64encode(credential_id).decode('utf-8')
        )
    ).first()
    if authentication is None:
        return None
    return authentication.user_id


@functools.cache
def _verify_origin(origin: str) -> bool:
    origin_parsed = urllib.parse.urlparse(origin)
    index_parsed = urllib.parse.urlparse(flask.url_for('.index', _external=True))
    return origin_parsed.scheme == index_parsed.scheme and origin_parsed.netloc == index_parsed.netloc


def get_webauthn_server() -> Fido2Server:
    """
    Get the FIDO2 webauthn server.

    :return: a Fido2Server instance
    """
    rp = PublicKeyCredentialRpEntity(
        name=flask.current_app.config['SERVICE_NAME'],
        id=(flask.current_app.config['SERVER_NAME'] or '').split(':')[0]
    )
    return Fido2Server(
        rp,
        attestation=AttestationConveyancePreference.NONE,
        verify_origin=_verify_origin
    )


def login(login: str, password: str) -> typing.Optional[logic.users.User]:
    """
    Authenticate a user and create an LDAP based user if necessary.

    :param login: the name, email or LDAP uid to use during authentication
    :param password: the password
    :return: the user or None
    """
    # convert to lower case to enforce case insensitivity
    login = login.lower().strip()
    # filter email + password or username + password or username (ldap)
    authentication_methods = Authentication.query.filter(
        db.or_(
            db.and_(Authentication.login['login'].astext == login,
                    Authentication.type == AuthenticationType.EMAIL),
            db.and_(Authentication.login['login'].astext == login,
                    Authentication.type == AuthenticationType.LDAP),
            db.and_(Authentication.login['login'].astext == login,
                    Authentication.type == AuthenticationType.OTHER)
        )
    ).all()

    for authentication_method in authentication_methods:
        if not authentication_method.confirmed:
            continue
        if authentication_method.type == AuthenticationType.LDAP and is_ldap_configured():
            if validate_user(login, password):
                return logic.users.User.from_database(authentication_method.user)
        elif authentication_method.type in {AuthenticationType.EMAIL, AuthenticationType.OTHER}:
            if _validate_password_authentication(authentication_method, password):
                return logic.users.User.from_database(authentication_method.user)

    # no matching authentication method in db
    if not authentication_methods and '@' not in login and is_ldap_configured():
        # try to authenticate against ldap, if login is no email
        if not validate_user(login, password):
            return None

        user = create_user_from_ldap(login)
        if user is None:
            return None
        try:
            add_ldap_authentication(user.id, login, password)
        except errors.AuthenticationMethodAlreadyExists:
            # user might have been created in the background already due to concurrent, duplicate requests
            pass
        return user
    return None


def login_via_api_token(api_token: str) -> typing.Optional[logic.users.User]:
    """
    Authenticate a user using an API token.

    :param api_token: the API token to use during authentication
    :return: the user or None
    """
    # convert to lower case to enforce case insensitivity
    api_token = api_token.lower().strip()
    username, password = api_token[:8], api_token[8:]
    authentication_methods = Authentication.query.filter(
        db.and_(Authentication.login['login'].astext == username,
                Authentication.type == AuthenticationType.API_TOKEN)
    ).all()

    for authentication_method in authentication_methods:
        if not authentication_method.confirmed:
            continue
        if _validate_password_authentication(authentication_method, password):
            api_log.create_log_entry(authentication_method.id, HTTPMethod.from_name(flask.request.method), flask.request.path)
            return logic.users.User.from_database(authentication_method.user)
    return None


def generate_api_access_token(
        user_id: int,
        description: typing.Optional[str]
) -> typing.Dict[str, typing.Optional[str]]:
    """
    Create a new API access token as an authentication method for a given user.

    :param user_id: the ID of an existing user
    :param description: an optional description
    :return: a dict containing the access token information
    """
    expiration_utc_datetime = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    expiration_utc_datetime_str = expiration_utc_datetime.strftime('%Y-%m-%d %H:%M:%S')

    access_token = secrets.token_hex(32)
    refresh_token = secrets.token_hex(32)

    refresh_token_login, refresh_token_password = refresh_token[:8], refresh_token[8:]
    db.session.add(Authentication(
        login={
            'access_token': access_token,
            'refresh_token_login': refresh_token_login,
            'refresh_token_hash': _hash_password(refresh_token_password),
            'expiration_utc_datetime': expiration_utc_datetime_str,
            'description': description
        },
        authentication_type=AuthenticationType.API_ACCESS_TOKEN,
        confirmed=True,
        user_id=user_id
    ))
    db.session.commit()
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expiration_utc_datetime': expiration_utc_datetime_str,
        'description': description
    }


def remove_expired_api_access_tokens() -> None:
    """
    Delete all expired API access tokens.
    """
    authentication_methods = Authentication.query.filter_by(
        type=AuthenticationType.API_ACCESS_TOKEN
    ).all()
    current_utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    for authentication_method in authentication_methods:
        expiration_utc_datetime_str = authentication_method.login['expiration_utc_datetime']
        expiration_utc_datetime = datetime.datetime.strptime(
            expiration_utc_datetime_str,
            '%Y-%m-%d %H:%M:%S'
        ).replace(tzinfo=datetime.timezone.utc)
        if expiration_utc_datetime <= current_utc_datetime:
            db.session.delete(authentication_method)
    db.session.commit()


def refresh_api_access_token(api_refresh_token: str) -> typing.Optional[typing.Dict[str, str]]:
    """
    Replace an API access token using its refresh token.

    :param api_refresh_token: the refresh token
    :return: a dict containing the new access token information
    """
    remove_expired_api_access_tokens()
    api_refresh_token = api_refresh_token.lower().strip()
    refresh_token_login, refresh_token_password = api_refresh_token[:8], api_refresh_token[8:]
    authentication_methods = Authentication.query.filter(
        db.and_(
            Authentication.login['refresh_token_login'].astext == refresh_token_login,
            Authentication.type == AuthenticationType.API_ACCESS_TOKEN
        )
    ).all()
    expiration_utc_datetime = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    expiration_utc_datetime_str = expiration_utc_datetime.strftime('%Y-%m-%d %H:%M:%S')

    for authentication_method in authentication_methods:
        if not authentication_method.confirmed:
            continue
        if _validate_password_hash(refresh_token_password, authentication_method.login['refresh_token_hash']):
            new_access_token = secrets.token_hex(32)
            new_refresh_token = secrets.token_hex(32)
            refresh_token_login, refresh_token_password = new_refresh_token[:8], new_refresh_token[8:]
            description = authentication_method.login['description']
            authentication_method.login = {
                'access_token': new_access_token,
                'refresh_token_login': refresh_token_login,
                'refresh_token_hash': _hash_password(refresh_token_password),
                'expiration_utc_datetime': expiration_utc_datetime_str,
                'description': description
            }
            db.session.add(authentication_method)
            db.session.commit()
            return {
                'access_token': new_access_token,
                'refresh_token': new_refresh_token,
                'expiration_utc_datetime': expiration_utc_datetime_str,
                'description': description
            }
    return None


def login_via_api_access_token(api_access_token: str) -> typing.Optional[logic.users.User]:
    """
    Authenticate a user using an API access token.

    :param api_access_token: the API access token to use for authentication
    :return: the user, or None
    """
    # convert to lower case to enforce case insensitivity
    api_access_token = api_access_token.lower().strip()
    remove_expired_api_access_tokens()
    authentication_methods = Authentication.query.filter(
        db.and_(
            Authentication.login['access_token'].astext == api_access_token,
            Authentication.type == AuthenticationType.API_ACCESS_TOKEN
        )
    ).all()

    for authentication_method in authentication_methods:
        if not authentication_method.confirmed:
            continue
        api_log.create_log_entry(authentication_method.id, HTTPMethod.from_name(flask.request.method), flask.request.path)
        return logic.users.User.from_database(authentication_method.user)
    return None


def login_via_api_refresh_token(api_refresh_token: str) -> typing.Optional[logic.users.User]:
    """
    Authenticate a user using a refresh token.

    :param api_refresh_token: the refresh token to use for authentication
    :return: the user, or None
    """
    # convert to lower case to enforce case insensitivity
    api_refresh_token = api_refresh_token.lower().strip()
    refresh_token_login, refresh_token_password = api_refresh_token[:8], api_refresh_token[8:]
    remove_expired_api_access_tokens()
    authentication_methods = Authentication.query.filter(
        db.and_(
            Authentication.login['refresh_token_login'].astext == refresh_token_login,
            Authentication.type == AuthenticationType.API_ACCESS_TOKEN
        )
    ).all()

    for authentication_method in authentication_methods:
        if not authentication_method.confirmed:
            continue
        if _validate_password_hash(refresh_token_password, authentication_method.login['refresh_token_hash']):
            api_log.create_log_entry(authentication_method.id, HTTPMethod.from_name(flask.request.method), flask.request.path)
            return logic.users.User.from_database(authentication_method.user)
    return None


def add_authentication_method(user_id: int, login: str, password: str, authentication_type: AuthenticationType) -> bool:
    """
    Add an authentication method for a user.

    :param user_id: the ID of an existing user
    :param login: the name, email or LDAP uid to use
    :param password: the password
    :param authentication_type: the type of authentication
    :return: whether the authentication method was added
    :raise errors.AuthenticationMethodAlreadyExists: if the authentication method exists already
    :raise errors.AuthenticationMethodWrong: if the authentication method was used in a wrong way
    :raise errors.LdapAccountAlreadyExist: if a user with this LDAP account already exists
    :raise errors.LdapAccountOrPasswordWrong: if the LDAP account and password could not be validated
    """
    if password is None or password == '':
        return False
    if login is None or login == '':
        return False
    # convert to lower case to enforce case insensitivity
    login = login.lower().strip()

    if authentication_type == AuthenticationType.LDAP:
        add_ldap_authentication(user_id, login, password)
        return True
    if authentication_type == AuthenticationType.EMAIL:
        add_email_authentication(user_id, login, password, False)
        return True
    return False


def remove_authentication_method(authentication_method_id: int) -> bool:
    """
    Remove an authentication method.

    :param authentication_method_id: the ID of an existing authentication method
    :raise errors.OnlyOneAuthenticationMethod: when this would remove the only
        authentication method for this user
    """
    authentication_method = Authentication.query.filter(Authentication.id == authentication_method_id).first()
    if authentication_method is None:
        return False
    if authentication_method.type not in {AuthenticationType.API_TOKEN, AuthenticationType.API_ACCESS_TOKEN}:
        authentication_methods_count = Authentication.query.filter(Authentication.user_id == authentication_method.user_id, Authentication.type != AuthenticationType.API_TOKEN, Authentication.type != AuthenticationType.API_ACCESS_TOKEN).count()
        if authentication_methods_count <= 1:
            raise errors.OnlyOneAuthenticationMethod('one authentication-method must at least exist, delete not possible')
    db.session.delete(authentication_method)
    db.session.commit()
    return True


def change_password_in_authentication_method(authentication_method_id: int, password: str) -> bool:
    """
    Change the password for a password-based authentication method.

    :param authentication_method_id: the ID of an authentication method
    :param password: the new password
    :return: whether the password was changed
    """
    if password is None or password == '':
        return False
    if authentication_method_id is None or authentication_method_id <= 0:
        return False
    authentication_method = Authentication.query.filter(Authentication.id == authentication_method_id).first()
    if authentication_method is None:
        return False
    if authentication_method.type not in {AuthenticationType.EMAIL, AuthenticationType.OTHER}:
        return False
    authentication_method.login = {'login': authentication_method.login['login'], 'bcrypt_hash': _hash_password(password)}
    db.session.add(authentication_method)
    db.session.commit()
    return True


def is_login_available(login: str) -> bool:
    """
    Return whether or not a login is still available for use.

    For password-based authentication, the login can only be used once.

    :param login: the login for which to check availability
    :return: whether the login is available
    """
    return Authentication.query.filter(Authentication.login['login'].astext == login).first() is None


def _create_two_factor_authentication_method(
        user_id: int,
        data: typing.Dict[str, typing.Any],
        active: bool = False
) -> TwoFactorAuthenticationMethod:
    """
    Create a new two-factor authentication method.

    :param user_id: the ID of an existing user
    :param data: the method data
    :param active: whether the new method should be active
    :return: the newly created method
    """
    two_factor_authentication_method = TwoFactorAuthenticationMethod(
        user_id=user_id,
        data=data,
        active=active
    )
    db.session.add(two_factor_authentication_method)
    db.session.commit()
    return two_factor_authentication_method


def get_two_factor_authentication_methods(
        user_id: int,
        active: typing.Optional[bool] = None
) -> typing.List[TwoFactorAuthenticationMethod]:
    """
    Get all two-factor authentication methods for a user.

    :param user_id: the ID of an existing user
    :param active: whether the queries need to be active, or None
    :return: a list containing all methods
    """
    query = TwoFactorAuthenticationMethod.query.filter_by(user_id=user_id)
    if active is not None:
        query = query.filter_by(active=active)
    return query.order_by(TwoFactorAuthenticationMethod.id).all()


def get_active_two_factor_authentication_methods(
        user_id: int
) -> typing.Sequence[TwoFactorAuthenticationMethod]:
    """
    Get the currently active two-factor authentication methods.

    :param user_id: the ID of an existing user
    :return: a list of active methods
    """
    return get_two_factor_authentication_methods(user_id=user_id, active=True)


def _set_two_factor_authentication_method_active(
        id: int,
        active: bool
) -> None:
    method = TwoFactorAuthenticationMethod.query.filter_by(id=id).first()
    if method is None:
        raise errors.TwoFactorAuthenticationMethodDoesNotExistError()
    method.active = active
    db.session.add(method)
    db.session.commit()


def activate_two_factor_authentication_method(
        id: int
) -> None:
    """
    Activate a two-factor authentication method.

    :param id: the ID of the method
    :raise errors.TwoFactorAuthenticationMethodDoesNotExistError: if no such method exists
    """
    _set_two_factor_authentication_method_active(id, active=True)


def deactivate_two_factor_authentication_method(
        id: int
) -> None:
    """
    Deactivate a two-factor authentication method.

    :param id: the ID of the method
    :raise errors.TwoFactorAuthenticationMethodDoesNotExistError: if no such method exists
    """
    _set_two_factor_authentication_method_active(id, active=False)


def delete_two_factor_authentication_method(
        id: int
) -> None:
    """
    Delete a two-factor authentication method.

    :param id: the ID of the method
    :raise errors.TwoFactorAuthenticationMethodDoesNotExistError: if no such method exists
    """
    deleted_method = TwoFactorAuthenticationMethod.query.filter_by(id=id).first()
    if deleted_method is None:
        raise errors.TwoFactorAuthenticationMethodDoesNotExistError()
    db.session.delete(deleted_method)
    db.session.commit()


def create_totp_two_factor_authentication_method(
        user_id: int,
        secret: str,
        description: str = ''
) -> TwoFactorAuthenticationMethod:
    """
    Create a new TOTP-based two-factor authentication method.

    :param user_id: the ID of an existing user
    :param secret: the TOTP secret
    :param description: a description
    :return: the newly created method
    """
    return _create_two_factor_authentication_method(
        user_id=user_id,
        data={
            'type': 'totp',
            'secret': secret,
            'description': description.strip()
        }
    )


def get_all_two_factor_fido2_passkey_credentials_for_user(
        user_id: int
) -> typing.Sequence[AttestedCredentialData]:
    """
    Get all FIDO2 passkey credentials for two-factor authentication methods for a given user.

    :param user_id: the ID of an existing user
    :return: a list of credentials
    """
    return [
        AttestedCredentialData(base64.b64decode(authentication_method.data['credential_data'].encode('utf-8')))
        for authentication_method in get_two_factor_authentication_methods(user_id)
        if authentication_method.data.get('type') == 'fido2_passkey'
    ]


def create_fido2_passkey_two_factor_authentication_method(
        user_id: int,
        credential_data: AttestedCredentialData,
        description: str = ''
) -> TwoFactorAuthenticationMethod:
    """
    Create a new FIDO2 Passkey two-factor authentication method.

    :param user_id: the ID of an existing user
    :param credential_data: the credential data
    :param description: a description
    :return: the newly created method
    """
    return _create_two_factor_authentication_method(
        user_id=user_id,
        data={
            'type': 'fido2_passkey',
            'credential_data': base64.b64encode(credential_data).decode('utf-8'),
            'description': description.strip()
        }
    )
