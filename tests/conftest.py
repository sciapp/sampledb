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

# restore possibly overridden configuration data from environment variables
sampledb.config.use_environment_configuration(env_prefix='SAMPLEDB_')
