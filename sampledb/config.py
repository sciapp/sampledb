# coding: utf-8
"""
Basic configuration for SampleDB

This configuration is the pure base, representing defaults. These values may be altered or expanded in several ways:
- For tests, the configuration is modified in tests/conftest.py.
- For local, interactive testing and demonstrations, the configuration is modified in demo.py.
- environment variables starting with the prefix SAMPLEDB_ will further override any hardcoded configuration data.
"""

import base64
import io
import json
import os
import requests
import typing
import sys
import sqlalchemy
from PIL import Image

from .utils import generate_secret_key, load_environment_configuration, ansi_color


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


def use_environment_configuration(env_prefix):
    """
    Uses configuration data from environment variables with a given prefix by setting the config modules variables.
    """
    config = load_environment_configuration(env_prefix)
    for name, value in config.items():
        globals()[name] = value


def check_config(
        config: typing.Mapping[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
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

    internal_config = {}

    missing_config_keys = REQUIRED_CONFIG_KEYS - defined_config_keys

    if missing_config_keys:
        print(
            ansi_color(
                'Missing required configuration values:\n -' +
                '\n - '.join(missing_config_keys) +
                '\n',
                color=31
            ),
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

    if 'JUPYTERHUB_URL' not in defined_config_keys and 'JUPYTERHUB_TEMPLATES_URL' not in defined_config_keys:
        print(
            'JupyterHub integration will be disabled, because none of following '
            'configuration values are defined:\n -',
            '\n - '.join(['JUPYTERHUB_URL', 'JUPYTERHUB_TEMPLATES_URL']),
            '\n',
            file=sys.stderr
        )
        show_config_info = True

    if 'DATAVERSE_URL' not in defined_config_keys:
        print(
            'Dataverse export will be disabled, because the configuration '
            'value DATAVERSE_URL is missing.\n'
            '\n',
            file=sys.stderr
        )
        show_config_info = True

    admin_password_set = 'ADMIN_PASSWORD' in defined_config_keys
    admin_username_set = 'ADMIN_USERNAME' in defined_config_keys
    admin_email_set = 'ADMIN_EMAIL' in defined_config_keys
    if admin_password_set or admin_username_set or admin_email_set:
        if not admin_password_set:
            if admin_username_set and admin_email_set:
                print(
                    'ADMIN_USERNAME and ADMIN_EMAIL are set, but '
                    'ADMIN_PASSWORD is missing. No admin user will be created.'
                    '\n',
                    file=sys.stderr
                )
            elif admin_username_set:
                print(
                    'ADMIN_USERNAME is set, but ADMIN_PASSWORD is missing. No '
                    'admin user will be created.'
                    '\n',
                    file=sys.stderr
                )
            elif admin_email_set:
                print(
                    'ADMIN_EMAIL is set, but ADMIN_PASSWORD is missing. No '
                    'admin user will be created.'
                    '\n',
                    file=sys.stderr
                )
        elif config['ADMIN_PASSWORD'] == '':
            print(
                'ADMIN_PASSWORD is an empty string. No admin user will be '
                'created.'
                '\n',
                file=sys.stderr
            )
        elif len(config['ADMIN_PASSWORD']) < 8:
            print(
                'ADMIN_PASSWORD is too short. No admin user will be created.'
                '\n',
                file=sys.stderr
            )
        elif can_run:
            engine = sqlalchemy.create_engine(config['SQLALCHEMY_DATABASE_URI'])
            user_table_exists = bool(engine.execute(
                "SELECT * "
                "FROM information_schema.columns "
                "WHERE table_name = 'users'"
            ).fetchall())
            if user_table_exists:
                users_exist = bool(engine.execute(
                    "SELECT * FROM users"
                ).fetchall())
            else:
                users_exist = False
            if users_exist:
                print(
                    'ADMIN_PASSWORD is set, but there already are users in '
                    'the database. No admin user will be created.'
                    '\n',
                    file=sys.stderr
                )
            else:
                admin_username = config.get('ADMIN_USERNAME', 'admin').lower()
                admin_email = config.get('ADMIN_EMAIL', config['CONTACT_EMAIL']).lower()
                print(
                    'A new admin user with the username "{}", the email '
                    'address "{}" and the given ADMIN_PASSWORD will be '
                    'created.'
                    '\n'.format(admin_username, admin_email),
                    file=sys.stderr
                )
                internal_config['ADMIN_INFO'] = (
                    admin_username, admin_email, config['ADMIN_PASSWORD']
                )
                if config['ADMIN_PASSWORD'] == 'password':
                    print(
                        ansi_color(
                            'You are using the default ADMIN_PASSWORD from the '
                            'SampleDB documentation. Please sign in and change your '
                            'password before making this SampleDB instance available '
                            'to other users.'
                            '\n',
                            color=33
                        ),
                        file=sys.stderr
                    )

        show_config_info = True

    if config['PDFEXPORT_LOGO_URL'] is not None:
        logo_url = config['PDFEXPORT_LOGO_URL']
        logo_image = None
        if logo_url.startswith('file://'):
            logo_path = logo_url[7:]
            try:
                logo_path = os.path.abspath(logo_path)
                _, logo_extension = os.path.splitext(logo_path)
                if logo_extension.lower() in ('.png', '.jpg', '.jpeg'):
                    logo_image = Image.open(logo_path)
                else:
                    print(
                        ansi_color(
                            f'Unsupported logo file format: {logo_extension}\n',
                            color=33
                        ),
                        file=sys.stderr
                    )
            except Exception:
                print(
                    ansi_color(
                        f'Unable to read logo file at: {logo_path}\n',
                        color=33
                    ),
                    file=sys.stderr
                )
        elif logo_url.startswith('http://') or logo_url.startswith('https://'):
            try:
                r = requests.get(logo_url, timeout=5)
                if r.status_code != 200:
                    print(
                        ansi_color(
                            f'Unable to read logo from: {logo_url}. Got status code: {r.status_code}\n',
                            color=33
                        ),
                        file=sys.stderr
                    )
                else:
                    logo_file = io.BytesIO(r.content)
                    logo_image = Image.open(logo_file)
            except Exception:
                print(
                    ansi_color(
                        f'Unable to read logo from: {logo_url}\n',
                        color=33
                    ),
                    file=sys.stderr
                )
        else:
            print(
                ansi_color(
                    f'Unable to read logo from: {logo_url}. The following URL schemes are supported: file, http, https.\n',
                    color=33
                ),
                file=sys.stderr
            )
        if logo_image:
            try:
                logo_width, logo_height = logo_image.size
                internal_config['PDFEXPORT_LOGO_ASPECT_RATIO'] = logo_width / logo_height
                logo_image = logo_image.convert('RGBA')
                background_image = Image.new('RGBA', logo_image.size, 'white')
                logo_image = Image.alpha_composite(background_image, logo_image)
                logo_file = io.BytesIO()
                logo_image.save(logo_file, "png")
                logo_png_data = logo_file.getvalue()
                logo_data_uri = 'data:image/png;base64,' + base64.b64encode(logo_png_data).decode('utf-8')
                internal_config['PDFEXPORT_LOGO_URL'] = logo_data_uri
            except Exception:
                print(
                    ansi_color(
                        f'Unable to read logo from: {logo_url}\n',
                        color=33
                    ),
                    file=sys.stderr
                )

    try:
        os.makedirs(config['FILE_STORAGE_PATH'], exist_ok=True)
        test_file_path = os.path.join(config['FILE_STORAGE_PATH'], '.exists')
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        open(test_file_path, 'a').close()
    except Exception:
        print(
            ansi_color(
                'Failed to write to the directory given as FILE_STORAGE_PATH.\n',
                color=31
            ),
            file=sys.stderr
        )
        can_run = False
        show_config_info = True

    if not isinstance(config['INVITATION_TIME_LIMIT'], int) or config['INVITATION_TIME_LIMIT'] <= 0:
        print(
            ansi_color(
                f'Expected INVITATION_TIME_LIMIT to be a positive integer, but got {config["INVITATION_TIME_LIMIT"]!r}\n',
                color=31
            ),
            file=sys.stderr
        )
        can_run = False
        show_config_info = True

    if not isinstance(config['EXTRA_USER_FIELDS'], dict):
        print(
            ansi_color(
                f'Expected EXTRA_USER_FIELDS to be a dictionary, but got {config["EXTRA_USER_FIELDS"]!r}\n',
                color=31
            ),
            file=sys.stderr
        )
        can_run = False
        show_config_info = True
    elif any(
            not isinstance(value, dict) or
            set(value.keys()) - {'name', 'placeholder'} or
            not isinstance(value.get('name', ''), (dict, str)) or
            not isinstance(value.get('placeholder', ''), (dict, str))
            for key, value in config['EXTRA_USER_FIELDS'].items()
    ):
        print(
            ansi_color(
                'Invalid EXTRA_USER_FIELDS.\n',
                color=31
            ),
            file=sys.stderr
        )
        can_run = False
        show_config_info = True

    if show_config_info:
        print(
            'For more information on setting SampleDB configuration, see: '
            'https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/'
            'administrator_guide/configuration.html',
            file=sys.stderr
        )

    if not can_run:
        exit(1)

    return internal_config


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
SERVICE_DESCRIPTION = {
    'en': SERVICE_NAME + ' is a database for sample and measurement metadata developed at PGI and JCNS.',
    'de': SERVICE_NAME + ' ist eine Datenbank für Proben- und Messungsmetadaten entwickelt am PGI und JCNS.'
}
SERVICE_IMPRINT = None
SERVICE_PRIVACY_POLICY = None
SAMPLEDB_HELP_URL = 'https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/#documentation'

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
JUPYTERHUB_NAME = 'JupyterHub'
JUPYTERHUB_URL = None
JUPYTERHUB_TEMPLATES_URL = None

# Dataverse settings
DATAVERSE_NAME = 'Dataverse'
DATAVERSE_URL = None
DATAVERSE_ROOT_IDS = ':root'

# PDF export settings
PDFEXPORT_LOGO_URL = None
PDFEXPORT_LOGO_ALIGNMENT = 'right'

# CSRF token time limit
# users may take a long time to fill out a form during an experiment
WTF_CSRF_TIME_LIMIT = 12 * 60 * 60

# invitation link time limit
INVITATION_TIME_LIMIT = 7 * 24 * 60 * 60

# other settings
ONLY_ADMINS_CAN_MANAGE_LOCATIONS = False
ONLY_ADMINS_CAN_CREATE_GROUPS = False
ONLY_ADMINS_CAN_DELETE_GROUPS = False
ONLY_ADMINS_CAN_CREATE_PROJECTS = False

DISABLE_USE_IN_MEASUREMENT = False

DISABLE_SUBPROJECTS = False

LOAD_OBJECTS_IN_BACKGROUND = False

ENFORCE_SPLIT_NAMES = False

BUILD_TRANSLATIONS = True
PYBABEL_PATH = 'pybabel'

EXTRA_USER_FIELDS = {}

SHOW_PREVIEW_WARNING = False

DISABLE_INLINE_EDIT = False

SHOW_OBJECT_TITLE = False

HIDE_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE = False

# environment variables override these values
use_environment_configuration(env_prefix='SAMPLEDB_')

# convert INVITATION_TIME_LIMIT in case it was set as a string
try:
    INVITATION_TIME_LIMIT = int(INVITATION_TIME_LIMIT)
except ValueError:
    pass

# parse values as integers
for config_name in {'MAX_CONTENT_LENGTH', }:
    value = globals().get(config_name)
    if isinstance(value, str):
        try:
            globals()[config_name] = int(value)
        except Exception:
            pass

# parse values as json
for config_name in {'SERVICE_DESCRIPTION', 'EXTRA_USER_FIELDS'}:
    value = globals().get(config_name)
    if isinstance(value, str) and value.startswith('{'):
        try:
            globals()[config_name] = json.loads(value)
        except Exception:
            pass

# parse boolean values
for config_name in {
    'ONLY_ADMINS_CAN_MANAGE_LOCATIONS',
    'ONLY_ADMINS_CAN_CREATE_GROUPS',
    'ONLY_ADMINS_CAN_DELETE_GROUPS',
    'ONLY_ADMINS_CAN_CREATE_PROJECTS',
    'DISABLE_USE_IN_MEASUREMENT',
    'DISABLE_SUBPROJECTS',
    'LOAD_OBJECTS_IN_BACKGROUND',
    'ENFORCE_SPLIT_NAMES',
    'BUILD_TRANSLATIONS',
    'SHOW_PREVIEW_WARNING',
    'SHOW_OBJECT_TITLE',
    'HIDE_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE',
}:
    value = globals().get(config_name)
    if isinstance(value, str):
        globals()[config_name] = value.lower() not in {'', 'false', 'no', 'off', '0'}
