# coding: utf-8
"""

"""

import getpass

import sampledb.config

sampledb.config.MAIL_SUPPRESS_SEND = True
sampledb.config.TEMPLATES_AUTO_RELOAD = True

sampledb.config.SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{0}:@localhost:5432/{0}'.format(getpass.getuser())

try:
    # for local testing
    import ldapaccount
    sampledb.config.TESTING_LDAP_LOGIN = ldapaccount.LDAP_LOGIN
    sampledb.config.TESTING_LDAP_PW = ldapaccount.LDAP_PW
except ImportError:
    # otherwise these must be set already (e.g. using the environment)
    assert hasattr(sampledb.config, 'TESTING_LDAP_LOGIN')
    assert hasattr(sampledb.config, 'TESTING_LDAP_PW')

sampledb.config.LDAP_NAME = 'PGI / JCNS'
sampledb.config.LDAP_SERVER = 'ldaps://ldap.iff.kfa-juelich.de'
sampledb.config.LDAP_USER_BASE_DN = 'cn=users,cn=accounts,dc=iff,dc=kfa-juelich,dc=de'
sampledb.config.LDAP_UID_FILTER='(uid={})'
sampledb.config.LDAP_NAME_ATTRIBUTE = 'cn'
sampledb.config.LDAP_MAIL_ATTRIBUTE = 'mail'
sampledb.config.LDAP_OBJECT_DEF = 'inetOrgPerson'
sampledb.config.LDAP_USER_DN = 'uid=' + sampledb.config.TESTING_LDAP_LOGIN + ',' + sampledb.config.LDAP_USER_BASE_DN
sampledb.config.LDAP_PASSWORD = sampledb.config.TESTING_LDAP_PW
sampledb.config.MAIL_SENDER = 'iffsamples@fz-juelich.de'
sampledb.config.MAIL_SERVER = 'mail.fz-juelich.de'
sampledb.config.CONTACT_EMAIL = 'iffsamples@fz-juelich.de'
sampledb.config.JUPYTERHUB_URL = 'iffjupyter.fz-juelich.de'

# restore possibly overridden configuration data from environment variables
sampledb.config.use_environment_configuration(env_prefix='SAMPLEDB_')
