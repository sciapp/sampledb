# coding: utf-8
"""
LDAP authentication for the cluster information database.
"""

import ldap3
import flask
from flask import abort

from .models import User, UserType


def user_dn(user_ldap_uid):
    base_dn = flask.current_app.config['LDAP_BASE_DN']
    user_dn = "uid={0},{1}".format(user_ldap_uid, base_dn)
    return user_dn


def search_user(user_ldap_uid):

    ldap_host = flask.current_app.config['LDAP_HOST']
    server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
    try:
        connection = ldap3.Connection(server, auto_bind=True)
    except ldap3.LDAPBindError:
        return None
    object_def = ldap3.ObjectDef('inetOrgPerson', connection)
    reader = ldap3.Reader(connection, object_def, user_dn(user_ldap_uid))
    reader.search()

    # search if user_dn exactly one user, not more
    if len(reader) != 1:
        return None
    return reader[0]


def validate_user(user_ldap_uid, password):
    if search_user(user_ldap_uid) is None:
        return False

    ldap_host = flask.current_app.config['LDAP_HOST']
    # if one user found in ldap
    # try to bind with credentials
    server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
    connection = ldap3.Connection(server, user=user_dn(user_ldap_uid), password=password, raise_exceptions=False)
    return bool(connection.bind())


def get_user_info(user_ldap_uid):
    user = search_user(user_ldap_uid)
    if user is None:
        return None
    if not user.mail:
        abort(400, 'Email in LDAP-account missing, please contact your administrator')
        return None
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
