# coding: utf-8
"""
Basic configuration for iffSamples

This configuration is the pure base, representing defaults. These values may be altered or expanded in several ways:
- For tests, the configuration is modified in tests/conftest.py.
- For local, interactive testing and demonstrations, the configuration is modified in demo.py.
- environment variables starting with the prefix SAMPLEDB_ will further override any hardcoded configuration data.
"""

import typing
import sys

from .utils import generate_secret_key, load_environment_configuration

REQUIRED_CONFIG_KEYS: typing.Set[str] = {
    'SQLALCHEMY_DATABASE_URI',
    'MAIL_SERVER',
    'MAIL_SENDER',
    'CONTACT_EMAIL',
}

LDAP_REQUIRED_CONFIG_KEYS: typing.Set[str] = {
    'LDAP_NAME',
    'LDAP_SERVER',
    'LDAP_USER_BASE_DN',
    'LDAP_UID_FILTER',
    'LDAP_NAME_ATTRIBUTE',
    'LDAP_MAIL_ATTRIBUTE',
    'LDAP_OBJECT_DEF',
}

JUPYTERHUB_REQUIRED_CONFIG_KEYS: typing.Set[str] = {
    'JUPYTERHUB_URL'
}


def use_environment_configuration(env_prefix):
    """
    Uses configuration data from environment variables with a given prefix by setting the config modules variables.
    """
    config = load_environment_configuration(env_prefix)
    for name, value in config.items():
        globals()[name] = value


def check_config(config: typing.Mapping[str, typing.Any]) -> None:
    """
    Check whether all neccessary configuration values are set.

    Print a warning if missing values will lead to reduced functionality.
    Exit if missing values will prevent SampleDB from working correctly.

    :param config: the config mapping
    """
    defined_config_keys = {
        key
        for key, value in config.items()
        if value is not None
    }

    show_config_info = False
    can_run = True

    missing_config_keys = REQUIRED_CONFIG_KEYS - defined_config_keys

    if missing_config_keys:
        print(
            'Missing required configuration values:\n -',
            '\n - '.join(missing_config_keys),
            '\n',
            file=sys.stderr
        )
        can_run = False
        show_config_info = True

    missing_config_keys = LDAP_REQUIRED_CONFIG_KEYS - defined_config_keys
    if missing_config_keys:
        print(
            'LDAP authentication will be disabled, because the following '
            'configuration values are missing:\n -',
            '\n - '.join(missing_config_keys),
            '\n',
            file=sys.stderr
        )
        show_config_info = True

    missing_config_keys = JUPYTERHUB_REQUIRED_CONFIG_KEYS - defined_config_keys
    if missing_config_keys:
        print(
            'JupyterHub integration will be disabled, because the following '
            'configuration values are missing:\n -',
            '\n - '.join(missing_config_keys),
            '\n',
            file=sys.stderr
        )
        show_config_info = True

    if show_config_info:
        print(
            'For more information on setting SampleDB configuration, see: '
            'https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/'
            'developer_guide/configuration.html',
            file=sys.stderr
        )

    if not can_run:
        exit(1)


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
LDAP_NAME = None
LDAP_SERVER = None
LDAP_USER_BASE_DN = None
LDAP_UID_FILTER = None
LDAP_NAME_ATTRIBUTE = None
LDAP_MAIL_ATTRIBUTE = None
LDAP_OBJECT_DEF = None
# LDAP credentials, may both be None if anonymous access is enabled
LDAP_USER_DN = None
LDAP_PASSWORD = None

# email settings
MAIL_SERVER = None
MAIL_SENDER = None
CONTACT_EMAIL = None

# branding and legal info
SERVICE_NAME = 'SampleDB'
SERVICE_DESCRIPTION = SERVICE_NAME + ' is the sample and measurement metadata database at PGI and JCNS.'
SERVICE_IMPRINT = None
SERVICE_PRIVACY_POLICY = None

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

# JupyterHub settings
JUPYTERHUB_URL = None

# CSRF token time limit
# users may take a long time to fill out a form during an experiment
WTF_CSRF_TIME_LIMIT = 12 * 60 * 60

# environment variables override these values
use_environment_configuration(env_prefix='SAMPLEDB_')
