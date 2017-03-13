# coding: utf-8
"""
LDAP authentication for the cluster information database.
"""

import ldap3
import flask
from ..models import User, UserType


def user_dn(user_ldap_uid):
    base_dn = flask.current_app.config['LDAP_BASE_DN']
    user_dn = "uid={0},{1}".format(user_ldap_uid, base_dn)
    return user_dn


def validate_user(user_ldap_uid, password):
    ldap_host = flask.current_app.config['LDAP_HOST']
    server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
    try:
        connection = ldap3.Connection(server, auto_bind=True)
        object_def = ldap3.ObjectDef('inetOrgPerson', connection)
        reader = ldap3.Reader(connection, object_def, user_dn(user_ldap_uid))
        reader.search()
    except ldap3.LDAPBindError:
        flask.flash('LDAPBindError')
        return False

    # search if user_dn exactly one user, not more
    if len(reader) != 1:
        return False
    # if one user found in ldap
    # try to bind with credentials. throws exception if credentials are invalid
    # raise_exceptions=False => more details found in connections.results , only for developing
    else:
        try:
            server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
            connection = ldap3.Connection(server, user=user_dn(user_ldap_uid), password=password)
            return bool(connection.bind())
        except ldap3.LDAPInvalidCredentials:
            flask.flash('LDAPInvalidCredentials')
            return False


def get_user_info(user_ldap_uid):
    ldap_host = flask.current_app.config['LDAP_HOST']
    server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
    try:
        connection = ldap3.Connection(server, auto_bind=True)
        object_def = ldap3.ObjectDef('inetOrgPerson', connection)
        reader = ldap3.Reader(connection, object_def, user_dn(user_ldap_uid))
        reader.search()
    except ldap3.LDAPBindError:
        flask.flash('LDAPBindError')
        return False

    # search if user_dn exactly one user, not more
    if len(reader) != 1:
        return False
    user = reader[0]
    if not user.mail:
        email = None
        flask.abort(400, 'Email in LDAP-account missing, please contact your administrator')
    else:
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
    print(user.name)
    print(user.email)
    print('------')
    return user
