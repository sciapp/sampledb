# coding: utf-8
"""
LDAP authentication for the cluster information database.
"""

from ldap3 import Server, Connection, ALL, Reader, ObjectDef
from flask import current_app

from demo.models import User, usertyps


def validate_user(login, password):
    base_dn = current_app.config['LDAP_BASE_DN']
    ldap_host = current_app.config['LDAP_HOST']
    server = Server(ldap_host, use_ssl=True, get_info=ALL)
    user_dn = "uid=" + login + ",ou=People,dc=iff,dc=kfa-juelich,dc=de"
    try:
        con = Connection(server, auto_bind=True)
        object_def = ObjectDef('inetOrgPerson', con)
        r = Reader(con, object_def, user_dn)
        r.search()
        # search if user_dn exactly one user, not more
        if len(r) != 1 or len(r) < 1:
            return False
        # if user found in ldap
        # try to bind with credentials. throws exception if credentials are
        # invalid
        else:
            server = Server('iffldap.iff.kfa-juelich.de', use_ssl=True, get_info=ALL)
            con = Connection(server, user=user_dn, password=password, raise_exceptions=False)
            erg = con.bind()
            if(not erg):
               return False
            else:
               return True
    except:
        return False


def get_gidNumber(login):
    base_dn = current_app.config['LDAP_BASE_DN']
    ldap_host = current_app.config['LDAP_HOST']
    server = Server(ldap_host, use_ssl=True, get_info=ALL)
    user_dn = "uid=" + login + ",ou=People,dc=iff,dc=kfa-juelich,dc=de"
    try:
        con = Connection(server, auto_bind=True)
        object_def = ObjectDef('posixAccount', con)
        r = Reader(con, object_def, user_dn)
        r.search()
        if len(r) != 1 or len(r) < 1:
            return None
        gidNumber = r[0].gidNumber
        return gidNumber
    except:
        return None


def get_user_info(login):
    base_dn = current_app.config['LDAP_BASE_DN']
    ldap_host = current_app.config['LDAP_HOST']
    server = Server(ldap_host, use_ssl=True, get_info=ALL)
    user_dn = "uid=" + login + ",ou=People,dc=iff,dc=kfa-juelich,dc=de"
    try:
        con = Connection(server, auto_bind=True)
        object_def = ObjectDef('inetorgperson', con)
        r = Reader(con, object_def, user_dn)
        r.search()
        # search if user_dn exactly one user, not more
        if len(r) != 1 or len(r) <1 :
            return None
        user = r[0]
        if 'mail' not in user:
            mail = None
        else:
            mail = user.mail[0]
        print(mail)
        if 'cn' not in user:
            cn = None
        else:
            cn = user.cn[0]

    except:
        return None

    user = User(
        name=cn,
        email=mail,
        usertype='person'
    )
    print(user.name)
    print(user.email)
    print(user)
    print('------')
    return user
