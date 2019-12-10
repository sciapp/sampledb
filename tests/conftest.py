# coding: utf-8
"""

"""

import getpass

import sampledb.config

sampledb.config.MAIL_SUPPRESS_SEND = True
sampledb.config.TEMPLATES_AUTO_RELOAD = True

sampledb.config.SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{0}:@localhost:5432/{0}'.format(getpass.getuser())
sampledb.config.MAIL_SENDER = 'sampledb@example.com'
sampledb.config.MAIL_SERVER = 'mail.example.com'
sampledb.config.CONTACT_EMAIL = 'sampledb@example.com'
sampledb.config.JUPYTERHUB_URL = 'example.com'
sampledb.config.LDAP_NAME = 'LDAP'

sampledb.config.TESTING_LDAP_UNKNOWN_LOGIN = 'unknown-login-for-sampledb-tests'
sampledb.config.TESTING_LDAP_WRONG_PASSWORD = 'wrong-password-for-sampledb-tests'

# restore possibly overridden configuration data from environment variables
sampledb.config.use_environment_configuration(env_prefix='SAMPLEDB_')
