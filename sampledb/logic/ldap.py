# coding: utf-8
"""
LDAP authentication for the cluster information database.
"""

import ldap3
import flask
from ..models import User, UserType


class NoEmailInLdapAccount(Exception):
    pass


class LdapAccountAlreadyExist(Exception):
    pass


class LdapAccountOrPasswordWrong(Exception):
    pass


def search_user(user_ldap_uid):
    ldap_host = flask.current_app.config['LDAP_HOST']
    user_dn = flask.current_app.config['LDAP_USER_DN']
    server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
    try:
        connection = ldap3.Connection(server, auto_bind=True)
    except ldap3.LDAPBindError:
        return None
    object_def = ldap3.ObjectDef('inetOrgPerson', connection)
    reader = ldap3.Reader(connection, object_def, user_dn, '(uid={})'.format(user_ldap_uid))
    reader.search()

    # search if user_dn exactly one user, not more
    if len(reader) != 1:
        return None
    return reader[0]


def get_posix_info(user_ldap_uid):
    ldap_host = flask.current_app.config['LDAP_HOST']
    user_dn = flask.current_app.config['LDAP_USER_DN']
    group_dn = flask.current_app.config['LDAP_GROUP_DN']

    server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
    try:
        connection = ldap3.Connection(server, auto_bind=True)
    except ldap3.LDAPBindError:
        return None
    object_def = ldap3.ObjectDef('posixAccount', connection)
    reader = ldap3.Reader(connection, object_def, user_dn, '(uid={})'.format(user_ldap_uid))
    reader.search()
    # filter must match exactly one group
    if len(reader) != 1:
        return None
    user = reader[0]

    object_def = ldap3.ObjectDef('posixGroup', connection)
    reader = ldap3.Reader(connection, object_def, group_dn, '(gidNumber={})'.format(user.gidNumber))
    reader.search()
    # filter must match exactly one group
    if len(reader) != 1:
        return None
    group = reader[0]
    return user, group


def validate_user(user_ldap_uid, password):
    user = search_user(user_ldap_uid)
    if user is None:
        return False
    if not user.mail:
        raise NoEmailInLdapAccount('Email in LDAP-account missing, please contact your administrator')
    ldap_host = flask.current_app.config['LDAP_HOST']
    # if one user found in ldap
    # try to bind with credentials
    server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
    user_dn = 'uid={},{}'.format(user_ldap_uid, flask.current_app.config['LDAP_USER_DN'])
    connection = ldap3.Connection(server, user=user_dn, password=password, raise_exceptions=False)
    return bool(connection.bind())


def get_user_info(user_ldap_uid):
    user = search_user(user_ldap_uid)
    if user is None:
        return None
    if not user.mail:
        raise NoEmailInLdapAccount('Email in LDAP-account missing, please contact your administrator')
    email = user.mail[0]
    if not user.cn:
        name = user_ldap_uid
    else:
        name = user.cn[0]

    user = User(
        name=name,
        email=email,
        type=UserType.PERSON
    )
    return user
