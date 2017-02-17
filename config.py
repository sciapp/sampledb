import os

basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = 'you-will-never-guess'
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://henkel:@localhost:5432/henkel'
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SQLALCHEMY_TRACK_MODIFICATIONS = False

LDAP_HOST = "ldaps://iffldap.iff.kfa-juelich.de"
LDAP_BASE_DN = "ou=People,dc=iff,dc=kfa-juelich,dc=de"

SECURITY_PASSWORD_SALT = 'my_precious_two'
