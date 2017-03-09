import base64
import getpass
import os
import ldapaccount

basedir = os.path.abspath(os.path.dirname(__file__))
user = getpass.getuser()

env_prefix = 'SAMPLEDB_'

CSRF_ENABLED = True
# Secret key is re-generated with each application start if it is not in the environment
SECRET_KEY = os.environ.get(env_prefix + 'SECRET_KEY', base64.b64encode(os.urandom(32)).decode('ascii'))

SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{0}:@localhost:5432/{0}'.format(user)
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SQLALCHEMY_TRACK_MODIFICATIONS = False

LDAP_HOST = "ldaps://iffldap.iff.kfa-juelich.de"
LDAP_BASE_DN = "ou=People,dc=iff,dc=kfa-juelich,dc=de"

MAIL_SERVER='mail.fz-juelich.de'
MAIL_SENDER = 'iffsamples@fz-juelich.de'
MAIL_SUPPRESS_SEND = True

TEMPLATES_AUTO_RELOAD = True

TESTING_LDAP_LOGIN = ldapaccount.LDAP_LOGIN
TESTING_LDAP_PW = ldapaccount.LDAP_PW