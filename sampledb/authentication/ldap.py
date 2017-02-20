# coding: utf-8
"""
LDAP authentication for the cluster information database.
"""

import ldap3
import flask

from .models import User, UserType


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
        # search if user_dn exactly one user, not more
        if len(reader) != 1:
            return False
        # if user found in ldap
        # TODO: "throws exception"? raise_exceptions=False? ???
        # try to bind with credentials. throws exception if credentials are
        # invalid
        else:
            server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
            connection = ldap3.Connection(server, user=user_dn(user_ldap_uid), password=password, raise_exceptions=False)
            return bool(connection.bind())
    except:
        return False


def get_user_info(user_ldap_uid):
    ldap_host = flask.current_app.config['LDAP_HOST']
    server = ldap3.Server(ldap_host, use_ssl=True, get_info=ldap3.ALL)
    try:
        connection = ldap3.Connection(server, auto_bind=True)
        object_def = ldap3.ObjectDef('inetOrgPerson', connection)
        reader = ldap3.Reader(connection, object_def, user_dn(user_ldap_uid))
        reader.search()
        # search if user_dn exactly one user, not more
        if len(reader) != 1:
            return None
        user = reader[0]
        if 'mail' not in user:
            # TODO: mail MUST NOT be None
            email = None
        else:
            email = user.mail[0]
        if 'cn' not in user:
            name = user_ldap_uid
        else:
            name = user.cn[0]

    except:
        return None

    user = User(
        name=name,
        email=email,
        user_type=UserType.PERSON
    )
    print(user.name)
    print(user.email)
    print(user)
    print('------')
    return user
