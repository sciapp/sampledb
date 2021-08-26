import bcrypt
import typing
import flask

from .. import logic, db
from .ldap import validate_user, create_user_from_ldap, is_ldap_configured
from ..models import Authentication, AuthenticationType, TwoFactorAuthenticationMethod, User
from . import errors, api_log


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _validate_password_hash(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


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
    :param confirmed: whether the authentication method has been confirmed already
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


def login(login: str, password: str) -> typing.Optional[User]:
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
                return authentication_method.user
        elif authentication_method.type in {AuthenticationType.EMAIL, AuthenticationType.OTHER}:
            if _validate_password_authentication(authentication_method, password):
                return authentication_method.user

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


def login_via_api_token(api_token: str) -> typing.Optional[User]:
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
            api_log.create_log_entry(authentication_method.id, getattr(api_log.HTTPMethod, flask.request.method, api_log.HTTPMethod.OTHER), flask.request.path)
            return authentication_method.user
    return None


def add_authentication_method(user_id: int, login: str, password: str, authentication_type: AuthenticationType) -> bool:
    """
    Add an authentication method for a user.

    :param user_id: the ID of an existing user
    :param login: the name, email or LDAP uid to use
    :param password: the password
    :param authentication_type: the type of authentication
    :return: whether or not the authentication method was added
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
    :return:
    """
    authentication_method = Authentication.query.filter(Authentication.id == authentication_method_id).first()
    if authentication_method is None:
        return False
    if authentication_method.type != AuthenticationType.API_TOKEN:
        authentication_methods_count = Authentication.query.filter(Authentication.user_id == authentication_method.user_id, Authentication.type != AuthenticationType.API_TOKEN).count()
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
        data: typing.Dict[str, typing.Any]
) -> TwoFactorAuthenticationMethod:
    """
    Create a new two factor authentication method.

    :param user_id: the ID of an existing user
    :param data: the method data
    :return: the newly created method
    """
    two_factor_authentication_method = TwoFactorAuthenticationMethod(
        user_id=user_id,
        data=data
    )
    db.session.add(two_factor_authentication_method)
    db.session.commit()
    return two_factor_authentication_method


def get_two_factor_authentication_methods(
        user_id: int
) -> typing.List[TwoFactorAuthenticationMethod]:
    """
    Get all two factor authentication methods for a user.

    :param user_id: the ID of an existing user
    :return: a list containing all methods
    """
    return TwoFactorAuthenticationMethod.query.filter_by(user_id=user_id).all()


def get_active_two_factor_authentication_method(
        user_id: int
) -> typing.Optional[TwoFactorAuthenticationMethod]:
    """
    Get the currently active two factor authentication method, or None.

    :param user_id: the ID of an existing user
    :return: the active method
    """
    return TwoFactorAuthenticationMethod.query.filter_by(user_id=user_id, active=True).first()


def activate_two_factor_authentication_method(
        id: int
) -> None:
    """
    Activate a two factor authentication method and deactivate all others.

    :rtype: object
    :param id: the ID of the method
    :raise errors.TwoFactorAuthenticationMethodDoesNotExistError: if no such method exists
    """
    activated_method = TwoFactorAuthenticationMethod.query.filter_by(id=id).first()
    if activated_method is None:
        raise errors.TwoFactorAuthenticationMethodDoesNotExistError()
    activated_method.active = True
    for method in TwoFactorAuthenticationMethod.query.filter_by(user_id=activated_method.user_id).all():
        if method.id != id:
            method.active = False
        db.session.add(method)
    db.session.commit()


def deactivate_two_factor_authentication_method(
        id: int
) -> None:
    """
    Deactivate a two factor authentication method.

    :param id: the ID of the method
    :raise errors.TwoFactorAuthenticationMethodDoesNotExistError: if no such method exists
    """
    deactivated_method = TwoFactorAuthenticationMethod.query.filter_by(id=id).first()
    if deactivated_method is None:
        raise errors.TwoFactorAuthenticationMethodDoesNotExistError()
    deactivated_method.active = False
    db.session.add(deactivated_method)
    db.session.commit()


def delete_two_factor_authentication_method(
        id: int
) -> None:
    """
    Delete a two factor authentication method.

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
        secret: str
) -> TwoFactorAuthenticationMethod:
    """
    Create a new TOTP-based two factor authentication method.

    :param user_id: the ID of an existing user
    :param secret: the TOTP secret
    :return: the newly created method
    """
    return _create_two_factor_authentication_method(
        user_id=user_id,
        data={
            'type': 'totp',
            'secret': secret
        }
    )
