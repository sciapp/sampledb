# coding: utf-8
"""
Basic configuration for iffSamples

This configuration is the pure base, representing defaults. These values may be altered or expanded in several ways:
- For tests, the configuration is modified in tests/conftest.py.
- For local, interactive testing and demonstrations, the configuration modified in demo.py.
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

CSRF_ENABLED = True

SECRET_KEY = generate_secret_key(num_bits=256)

SQLALCHEMY_TRACK_MODIFICATIONS = False

LDAP_HOST = "ldaps://iffldap.iff.kfa-juelich.de"
LDAP_USER_DN = "ou=People,dc=iff,dc=kfa-juelich,dc=de"
LDAP_GROUP_DN = "ou=Groups,dc=iff,dc=kfa-juelich,dc=de"
LDAP_NAME = 'PGI / JCNS'

MAIL_SERVER='mail.fz-juelich.de'
MAIL_SENDER = 'iffsamples@fz-juelich.de'
CONTACT_EMAIL = 'f.rhiem@fz-juelich.de'

SERVICE_NAME = 'iffSamples'
SERVICE_DESCRIPTION = SERVICE_NAME + ' is the sample and measurement metadata database at PGI and JCNS.'

FILE_STORAGE_PATH = '/tmp/sampledb/'

MIME_TYPES = {
    '.txt': 'text/plain',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.pdf': 'application/pdf'
}


# environment variables override these values
use_environment_configuration(env_prefix='SAMPLEDB_')
