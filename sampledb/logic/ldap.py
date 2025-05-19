# coding: utf-8
"""
Implementation of LDAP authentication.
"""
import typing

import ldap3
import ldap3.core.exceptions
import ldap3.utils.conv
import flask

from ..models import Authentication, AuthenticationType, UserType
from .. import db
from . import errors
from . import users
from ..config import LDAP_REQUIRED_CONFIG_KEYS


def is_ldap_configured() -> bool:
    """
    Check whether all required LDAP configuration values are set.

    :return: whether all values are set, False otherwise
    """
    return all(
        flask.current_app.config[key]
        for key in LDAP_REQUIRED_CONFIG_KEYS
    )


def _get_ldap_server_pool() -> ldap3.ServerPool:
    ldap_server_urls = flask.current_app.config['LDAP_SERVER']
    connect_timeout = flask.current_app.config['LDAP_CONNECT_TIMEOUT']
    servers = []
    for ldap_server_url in ldap_server_urls.split(','):
        ldap_server_url = ldap_server_url.strip()
        if ldap_server_url:
            servers.append(ldap3.Server(ldap_server_url, use_ssl=True, get_info=ldap3.ALL, connect_timeout=connect_timeout))
    return ldap3.ServerPool(servers=servers, pool_strategy=ldap3.ROUND_ROBIN, active=True, exhaust=True)


def _get_user_dn_and_attributes(user_ldap_uid: str, attributes: typing.Sequence[str] = ()) -> typing.Optional[typing.Sequence[typing.Any]]:
    user_base_dn = flask.current_app.config['LDAP_USER_BASE_DN']
    uid_filter = flask.current_app.config['LDAP_UID_FILTER']
    object_def = flask.current_app.config['LDAP_OBJECT_DEF']
    user_dn = flask.current_app.config['LDAP_USER_DN']
    password = flask.current_app.config['LDAP_PASSWORD']
    try:
        server_pool = _get_ldap_server_pool()
        connection = ldap3.Connection(server_pool, user=user_dn, password=password, auto_bind=ldap3.AUTO_BIND_NO_TLS, client_strategy=ldap3.SAFE_SYNC)
        object_def = ldap3.ObjectDef(object_def, connection)
        reader = ldap3.Reader(connection, object_def, user_base_dn, uid_filter.format(ldap3.utils.conv.escape_filter_chars(user_ldap_uid)))
        reader.search(attributes)  # type: ignore[no-untyped-call]
        # search if uid matches exactly one user, not more
        if len(reader) != 1:
            return None
        user_attributes = [reader[0].entry_dn]
        for attribute in attributes:
            value = getattr(reader[0], attribute, None)
            if value:
                user_attributes.append(value[0])
            else:
                user_attributes.append(None)
        return user_attributes
    except ldap3.core.exceptions.LDAPException:
        return None


def validate_user(user_ldap_uid: str, password: str) -> bool:
    """
    Return whether or not a user with this LDAP uid and password exists.

    This will return False if the uid is not unique, even if the password
    matches one of the users, to avoid conflicts.

    :param user_ldap_uid: the LDAP uid of a user
    :param password: the user's LDAP password
    :return: whether the user credentials are correct or not
    :raise errors.LDAPNotConfiguredError: when LDAP is not configured
    :raise errors.NoEmailInLDAPAccountError: when a user with the UID exists,
        but the LDAP_MAIL_ATTRIBUTE is not set for them
    """
    if not is_ldap_configured():
        raise errors.LDAPNotConfiguredError()

    mail_attribute = flask.current_app.config['LDAP_MAIL_ATTRIBUTE']
    user = _get_user_dn_and_attributes(user_ldap_uid, [mail_attribute])
    if user is None:
        return False
    user_dn, mail = user
    if mail is None:
        raise errors.NoEmailInLDAPAccountError('Email in LDAP-account missing, please contact your administrator')
    # try to bind with user credentials if a matching user exists
    try:
        server_pool = _get_ldap_server_pool()
        connection = ldap3.Connection(server_pool, user=user_dn, password=password, client_strategy=ldap3.SAFE_SYNC)
        return bool(connection.bind()[0])
    except ldap3.core.exceptions.LDAPException:
        return False


def create_user_from_ldap(user_ldap_uid: str) -> typing.Optional[users.User]:
    """
    Create a new user from LDAP information.

    The user's name is read from the LDAP_NAME_ATTRIBUTE, if the attribute
    is set, or the LDAP uid is used otherwise. Their email is read from the
    LDAP_MAIL_ATTRIBUTE.

    :param user_ldap_uid: the LDAP uid of a user
    :return: the newly created user or None, if information is missing
    :raise errors.LDAPNotConfiguredError: when LDAP is not configured
    :raise errors.NoEmailInLDAPAccountError: when the LDAP_MAIL_ATTRIBUTE is
        not set for the user
    """
    if not is_ldap_configured():
        raise errors.LDAPNotConfiguredError()

    name_attribute = flask.current_app.config['LDAP_NAME_ATTRIBUTE']
    mail_attribute = flask.current_app.config['LDAP_MAIL_ATTRIBUTE']
    user = _get_user_dn_and_attributes(
        user_ldap_uid,
        attributes=(name_attribute, mail_attribute)
    )
    if user is None:
        return None
    name, email = user[1:]
    if not email:
        raise errors.NoEmailInLDAPAccountError('There is no email set for your LDAP account. Please contact your administrator.')
    if not name:
        name = user_ldap_uid
    login = user_ldap_uid.lower().strip()
    authentication_methods = Authentication.query.filter(
        db.and_(Authentication.login['login'].astext == login,
                Authentication.type == AuthenticationType.LDAP)
    ).all()
    if not authentication_methods:
        return users.create_user(
            name=name,
            email=email,
            type=UserType.PERSON
        )
    return users.get_user(authentication_methods[0].user_id)
