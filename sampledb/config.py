# coding: utf-8
"""
Basic configuration for iffSamples

This configuration is the pure base, representing defaults. These values may be altered or expanded in several ways:
- For tests, the configuration is modified in tests/conftest.py.
- For local, interactive testing and demonstrations, the configuration is modified in demo.py.
- environment variables starting with the prefix SAMPLEDB_ will further override any hardcoded configuration data.
"""

from .utils import generate_secret_key, load_environment_configuration


def use_environment_configuration(env_prefix):
    """
    Uses configuration data from environment variables with a given prefix by setting the config modules variables.
    """
    config = load_environment_configuration(env_prefix)
    for name, value in config.items():
        globals()[name] = value


# prefix for all routes (used by run script)
SERVER_PATH = '/'

# whether to use CSRF protection
# see: https://flask-wtf.readthedocs.io/en/stable/config.html
CSRF_ENABLED = True

# secret key for Flask, wtforms and more
# see: http://flask.pocoo.org/docs/1.0/config/#SECRET_KEY
# automatically generated default, but should be replaced using environment variable SAMPLEDB_SECRET_KEY
SECRET_KEY = generate_secret_key(num_bits=256)

# whether or not SQLAlchemy should track modifications
# see: http://flask-sqlalchemy.pocoo.org/2.3/config/
# deprecated and should stay disabled, as we manually add modified objects
SQLALCHEMY_TRACK_MODIFICATIONS = False

# LDAP settings
LDAP_NAME = 'PGI / JCNS'
LDAP_SERVER = "ldaps://iffldap.iff.kfa-juelich.de"
LDAP_USER_BASE_DN = "ou=People,dc=iff,dc=kfa-juelich,dc=de"
LDAP_UID_FILTER = "(uid={})"
LDAP_NAME_ATTRIBUTE = "cn"
LDAP_MAIL_ATTRIBUTE = "mail"
LDAP_OBJECT_DEF = 'inetOrgPerson'
# LDAP credentials, may both be None if anonymous access is enabled
LDAP_USER_DN = None
LDAP_PASSWORD = None

# email settings
MAIL_SERVER = 'mail.fz-juelich.de'
MAIL_SENDER = 'iffsamples@fz-juelich.de'
CONTACT_EMAIL = 'f.rhiem@fz-juelich.de'

# branding and legal info
SERVICE_NAME = 'iffSamples'
SERVICE_DESCRIPTION = SERVICE_NAME + ' is the sample and measurement metadata database at PGI and JCNS.'
SERVICE_IMPRINT = 'https://pgi-jcns.fz-juelich.de/portal/pages/imprint.html'
SERVICE_PRIVACY_POLICY = 'https://pgi-jcns.fz-juelich.de/portal/pages/privacypolicy.html'

# location for storing files
# in this directory, per-action subdirectories will be created, containing
# per-object subdirectories, containing the actual files
FILE_STORAGE_PATH = '/tmp/sampledb/'

# a map of file extensions and the MIME types they should be handled as
# this is used to determine which user uploaded files should be served as
# images (those with an image/ MIME type) in the object view and which support
# a preview.
# files with extensions not listed here only support being downloaded.
MIME_TYPES = {
    '.txt': 'text/plain',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.pdf': 'application/pdf'
}


# environment variables override these values
use_environment_configuration(env_prefix='SAMPLEDB_')
