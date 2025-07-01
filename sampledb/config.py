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
import sys
import typing

import pytz
import pytz.exceptions
import requests
import sqlalchemy
from PIL import Image

from .utils import generate_secret_key, load_environment_configuration, ansi_color, text_to_bool
from .frontend.labels import PAGE_SIZE_KEYS, PAGE_SIZES
from .models.notifications import NotificationMode, NotificationType

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

OIDC_REQUIRED_CONFIG_KEYS: typing.Set[str] = {
    'OIDC_NAME',
    'OIDC_ISSUER',
    'OIDC_CLIENT_ID',
    'OIDC_CLIENT_SECRET',
}


def use_environment_configuration(env_prefix: str) -> None:
    """
    Uses configuration data from environment variables with a given prefix by setting the config modules variables.
    """
    config = load_environment_configuration(env_prefix)
    for name, value in config.items():
        globals()[name] = value
    parse_configuration_values()


def parse_configuration_values() -> None:
    """
    Convert configuration values from strings to integers, booleans or JSON objects.
    """
    # parse values as integers
    for config_name in [
        'INVITATION_TIME_LIMIT',
        'MAX_CONTENT_LENGTH',
        'MAX_BATCH_SIZE',
        'VALID_TIME_DELTA',
        'DOWNLOAD_SERVICE_TIME_LIMIT',
        'TYPEAHEAD_OBJECT_LIMIT',
        'LDAP_CONNECT_TIMEOUT',
        'TEMPORARY_FILE_TIME_LIMIT',
        'SHARED_DEVICE_SIGN_OUT_MINUTES',
        'MIN_NUM_TEXT_CHOICES_FOR_SEARCH',
        'PDFEXPORT_LOGO_WIDTH',
    ]:
        value = globals().get(config_name)
        if isinstance(value, str):
            try:
                globals()[config_name] = int(value)
            except Exception:
                pass

    # parse values as json
    for config_name in [
        'SERVICE_DESCRIPTION',
        'EXTRA_USER_FIELDS',
        'DOWNLOAD_SERVICE_WHITELIST',
        'LABEL_PAPER_FORMATS',
        'DEFAULT_NOTIFICATION_MODES'
    ]:
        value = globals().get(config_name)
        if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
            try:
                globals()[config_name] = json.loads(value)
            except Exception:
                pass

    # parse boolean values
    for config_name in [
        'DISABLE_USER_INVITATIONS',
        'ONLY_ADMINS_CAN_MANAGE_LOCATIONS',
        'ONLY_ADMINS_CAN_CREATE_GROUPS',
        'ONLY_ADMINS_CAN_DELETE_GROUPS',
        'ONLY_ADMINS_CAN_CREATE_PROJECTS',
        'ONLY_ADMINS_CAN_DELETE_PROJECTS',
        'ONLY_ADMINS_CAN_MANAGE_GROUP_CATEGORIES',
        'DISABLE_USE_IN_MEASUREMENT',
        'DISABLE_SUBPROJECTS',
        'ENFORCE_SPLIT_NAMES',
        'BUILD_TRANSLATIONS',
        'SHOW_PREVIEW_WARNING',
        'SHOW_OBJECT_TITLE',
        'FULL_WIDTH_OBJECTS_TABLE',
        'HIDE_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE',
        'DISABLE_INLINE_EDIT',
        'ENABLE_BACKGROUND_TASKS',
        'ENABLE_MONITORINGDASHBOARD',
        'ENABLE_ANONYMOUS_USERS',
        'ENABLE_NUMERIC_TAGS',
        'SHOW_UNHANDLED_OBJECT_RESPONSIBILITY_ASSIGNMENTS',
        'SHOW_LAST_PROFILE_UPDATE',
        'USE_TYPEAHEAD_FOR_OBJECTS',
        'DISABLE_INSTRUMENTS',
        'ENABLE_FUNCTION_CACHES',
        'ENABLE_CONTENT_SECURITY_POLICY',
        'ENABLE_ELN_FILE_IMPORT',
        'ELN_FILE_IMPORT_ALLOW_HTTP',
        'ENABLE_FEDERATION_DISCOVERABILITY',
        'ENABLE_WEBHOOKS_FOR_USERS',
        'WEBHOOKS_ALLOW_HTTP',
        'ENABLE_FIDO2_PASSKEY_AUTHENTICATION',
        'DISABLE_OUTDATED_USE_AS_TEMPLATE',
        'DISABLE_TOPICS',
        'ENABLE_FEDERATED_LOGIN',
        'ENABLE_FEDERATED_LOGIN_CREATE_NEW_USER',
        'OIDC_ONLY',
        'OIDC_DISABLE_NONCE',
        'OIDC_ACCESS_TOKEN_AS_API_KEY',
        'OIDC_ACCESS_TOKEN_ALLOW_INTROSPECTION',
        'WORKFLOW_VIEW_MODALS',
        'WORKFLOW_VIEW_COLLAPSED',
    ]:
        value = globals().get(config_name)
        if isinstance(value, str):
            globals()[config_name] = text_to_bool(value)


def is_download_service_whitelist_valid() -> bool:
    # check if paths and user ids from DOWNLOAD_SERVICE_WHITELIST are valid
    for path, user_ids in DOWNLOAD_SERVICE_WHITELIST.items():
        norm_path = os.path.normpath(os.path.join(os.path.sep, path))
        if norm_path != path:
            print(
                ansi_color(
                    'DOWNLOAD_SERVICE_WHITELIST: Please use a normalized '
                    'paths.'
                    '\n',
                    color=33
                ),
                file=sys.stderr
            )
            return False

        for user_id in user_ids:
            if type(user_id) is not int:
                print(
                    ansi_color(
                        'DOWNLOAD_SERVICE_WHITELIST: Please use a number for '
                        'the user IDs.'
                        '\n',
                        color=33
                    ),
                    file=sys.stderr
                )
                return False
    return True


def is_label_paper_formats_valid() -> bool:
    """check if paper formats from LABEL_PAPER_FORMATS are valid"""

    if not isinstance(LABEL_PAPER_FORMATS, list):
        print(ansi_color('LABEL_PAPER_FORMATS: Must be a list of dictionaries.\n', color=31))
        return False
    is_valid = True
    for i, format_definition in enumerate(LABEL_PAPER_FORMATS, start=1):
        if not isinstance(format_definition, dict):
            print(ansi_color('LABEL_PAPER_FORMATS: Must be a list of dictionaries.\n', color=31))
            return False
        str_fields = ['format_name']
        int_fields = ['labels_in_row', 'labels_in_col', 'qr_code_width', 'paper_format']
        float_fields = ['label_width', 'label_height', 'margin_horizontal', 'margin_vertical']
        for key, value in format_definition.items():
            if key in int_fields:
                int_fields.remove(key)
                if not isinstance(value, int):
                    is_valid = False
                    print(ansi_color(f'LABEL_PAPER_FORMATS: {key} must be a whole number in format definition {i}.\n', color=31))
                if key == 'qr_code_width':
                    if value < 4:
                        format_definition['qr_code_width'] = 4
                        print(ansi_color(f'LABEL_PAPER_FORMATS: {key} in format definition {i} is less than 4. Value set to 4.\n', color=33))
                    elif value > 150:
                        format_definition['qr_code_width'] = 150
                        print(ansi_color(f'LABEL_PAPER_FORMATS: {key} in format definition {i} is greater than 150. Value set to 150.\n', color=33))
                elif value < 0:
                    is_valid = False
                    print(ansi_color(f'LABEL_PAPER_FORMATS: {key} must be greater than 0 in format definition {i}.\n', color=31))
            elif key in float_fields:
                float_fields.remove(key)
                if not isinstance(value, (int, float)):
                    is_valid = False
                    print(ansi_color(f'LABEL_PAPER_FORMATS: {key} must be a number in format definition {i}.\n', color=31))
                if value < 0:
                    is_valid = False
                    print(ansi_color(f'LABEL_PAPER_FORMATS: {key} must be greater than 0 in format definition {i}.\n', color=31))
            elif key in str_fields:
                str_fields.remove(key)
                if not isinstance(value, str) and not isinstance(value, dict):
                    is_valid = False
                    print(ansi_color(f'LABEL_PAPER_FORMATS: {key} must be a string in format definition {i}.\n', color=31))
            else:
                print(ansi_color(f'LABEL_PAPER_FORMATS: {key} is an Unknown key in format definition {i}.\n', color=33))
        if not is_valid:
            return False

        if len(str_fields) > 0 or len(int_fields) > 0 or len(float_fields) > 0:
            for key in str_fields + int_fields + float_fields:
                print(ansi_color(f'LABEL_PAPER_FORMATS: {key} is missing in format definition {i}.\n', color=31))
            return False

        if format_definition['paper_format'] < 0 or format_definition['paper_format'] >= len(PAGE_SIZE_KEYS):
            print(ansi_color(f'LABEL_PAPER_FORMATS: invalid paper_format in format definition {i}.\n', color=31))
            return False
        page_size = PAGE_SIZES[PAGE_SIZE_KEYS[format_definition['paper_format']]]
        page_width = page_size[0]
        page_height = page_size[1]
        used_page_width = format_definition['labels_in_row'] * format_definition['label_width'] + (format_definition['labels_in_row'] - 1) * format_definition['margin_horizontal']
        used_page_height = format_definition['labels_in_col'] * format_definition['label_height'] + (format_definition['labels_in_col'] - 1) * format_definition['margin_vertical']
        if page_width < used_page_width or page_height < used_page_height:
            print(ansi_color(f'LABEL_PAPER_FORMATS: page is too small for labels in format definition {i}.\n', color=31))
            return False

    return is_valid


def is_default_notification_modes_valid() -> bool:
    """
    Check if the default notification mode dict is valid.
    """
    if DEFAULT_NOTIFICATION_MODES is None:
        return True
    if not isinstance(DEFAULT_NOTIFICATION_MODES, dict):
        print(ansi_color(f'DEFAULT_NOTIFICATION_MODES must be dict, but got {type(DEFAULT_NOTIFICATION_MODES)}.\n', color=31))
        return False
    for key, value in DEFAULT_NOTIFICATION_MODES.items():
        valid_keys = [notification_type.name.upper() for notification_type in NotificationType] + ["DEFAULT"]
        if key not in valid_keys:
            print(ansi_color(f'DEFAULT_NOTIFICATION_MODES keys must be one of {valid_keys!r}, but got {key!r}.\n', color=31))
            return False
        valid_modes = [notification_mode.name.upper() for notification_mode in NotificationMode]
        if value not in valid_modes:
            print(ansi_color(f'DEFAULT_NOTIFICATION_MODES values must be one of {valid_modes!r}, but got {value!r}.\n', color=31))
            return False
    return True


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

    internal_config: typing.Dict[str, typing.Any] = {}

    missing_config_keys = REQUIRED_CONFIG_KEYS - defined_config_keys

    if missing_config_keys:
        print(
            ansi_color(
                'Missing required configuration values:\n - ' +
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

    missing_config_keys = OIDC_REQUIRED_CONFIG_KEYS - defined_config_keys
    if missing_config_keys:
        print(
            'OIDC authentication will be disabled, because the following '
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

    if 'SCICAT_API_URL' not in defined_config_keys:
        print(
            'SciCat export will be disabled, because the configuration '
            'value SCICAT_API_URL is missing.\n'
            '\n',
            file=sys.stderr
        )
        show_config_info = True
    elif 'SCICAT_FRONTEND_URL' not in defined_config_keys:
        print(
            'SciCat export will be disabled, because the configuration '
            'value SCICAT_FRONTEND_URL is missing.\n'
            '\n',
            file=sys.stderr
        )
        show_config_info = True

    if 'DOWNLOAD_SERVICE_URL' not in defined_config_keys:
        print(
            'Download service will be disabled, because the configuration '
            'value DOWNLOAD_SERVICE_URL is missing.\n'
            '\n',
            file=sys.stderr
        )
        show_config_info = True
    elif 'DOWNLOAD_SERVICE_SECRET' not in defined_config_keys:
        print(
            'Download service will be disabled, because the configuration '
            'value DOWNLOAD_SERVICE_SECRET is missing.\n'
            '\n',
            file=sys.stderr
        )
        show_config_info = True

    if 'ENABLE_FEDERATED_LOGIN' not in defined_config_keys and 'ENABLE_FEDERATED_LOGIN_CREATE_NEW_USER' in defined_config_keys:
        print(
            'The configuration value ENABLE_FEDERATED_LOGIN_CREATE_NEW_USER '
            'will have no effect, because the configuration value '
            'ENABLE_FEDERATED_LOGIN is missing.\n'
            '\n'
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
            engine = sqlalchemy.create_engine(config['SQLALCHEMY_DATABASE_URI'], **config['SQLALCHEMY_ENGINE_OPTIONS'])
            with engine.begin() as connection:
                user_table_exists = bool(connection.execute(sqlalchemy.text(
                    "SELECT * "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'users'"
                )).fetchall())
                if user_table_exists:
                    users_exist = bool(connection.execute(sqlalchemy.text(
                        "SELECT * FROM users"
                    )).fetchall())
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
                    f'A new admin user with the username "{admin_username}", the email '
                    f'address "{admin_email}" and the given ADMIN_PASSWORD will be '
                    'created.'
                    '\n',
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

    if can_run:
        engine = sqlalchemy.create_engine(config['SQLALCHEMY_DATABASE_URI'], **config['SQLALCHEMY_ENGINE_OPTIONS'])
        with engine.begin() as connection:
            files_table_with_data_exists = bool(connection.execute(sqlalchemy.text(
                """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'files' AND column_name = 'data'
                """
            )).scalar())
            if files_table_with_data_exists:
                local_files_exist = bool(connection.execute(sqlalchemy.text(
                    """
                    SELECT COUNT(*)
                    FROM files
                    WHERE data->>'storage' = 'local'
                    """
                )).scalar())
            else:
                # if there is no file table with a data column, local files may
                # still exist from a version of SampleDB before the data column
                # was added
                local_files_exist = bool(connection.execute(sqlalchemy.text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.columns
                    WHERE table_name = 'files' AND column_name = 'original_file_name'
                    """
                )).scalar())
            if local_files_exist:
                print(
                    ansi_color(
                        'There are files with "local" storage. These are not '
                        'supported anymore starting with SampleDB 0.26.0. '
                        'Please move them to "database" storage using an '
                        'earlier version of SampleDB. For more information, '
                        'see: '
                        'https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/deprecated_features.html#local-file-storage'
                        '\n',
                        color=31
                    ),
                    file=sys.stderr
                )
                can_run = False
                show_config_info = True
            elif 'FILE_STORAGE_PATH' in defined_config_keys:
                print(
                    ansi_color(
                        'FILE_STORAGE_PATH is set, however files with "local" storage '
                        'are not supported anymore starting with SampleDB 0.26.0. '
                        'Please unset the FILE_STORAGE_PATH config variable and do '
                        'not mount a directory for local file storage. For more '
                        'information, see: '
                        'https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/deprecated_features.html#local-file-storage'
                        '\n',
                        color=31
                    ),
                    file=sys.stderr
                )
                can_run = False
                show_config_info = True

    internal_config['PDFEXPORT_LOGO_WIDTH'] = min(200, max(0, config['PDFEXPORT_LOGO_WIDTH']))
    if config['PDFEXPORT_LOGO_URL'] is not None:
        logo_url = config['PDFEXPORT_LOGO_URL']
        logo_image: typing.Optional[Image.Image] = None
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

    if config['TIMEZONE']:
        try:
            pytz.timezone(config['TIMEZONE'])
        except pytz.exceptions.UnknownTimeZoneError:
            print(
                ansi_color(
                    'Unknown time zone.\n',
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

    if not is_download_service_whitelist_valid():
        can_run = False
        show_config_info = True

    if not is_label_paper_formats_valid():
        can_run = False
        show_config_info = True

    if not is_default_notification_modes_valid():
        can_run = False
        show_config_info = True

    if config['OIDC_CREATE_ACCOUNT'] not in ('no', 'deny_existing', 'auto_link'):
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
        sys.exit(1)

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

# sameSite attribute for cookies
# see: https://flask.palletsprojects.com/en/2.2.x/security/#set-cookie-options
SESSION_COOKIE_SAMESITE = 'Lax'

# SQLAlchemy settings
SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {"options": "-c timezone=utc"}}

# LDAP settings
LDAP_NAME = None
LDAP_SERVER = None
LDAP_USER_BASE_DN = None
LDAP_UID_FILTER = None
LDAP_NAME_ATTRIBUTE = None
LDAP_MAIL_ATTRIBUTE = None
LDAP_OBJECT_DEF = None
LDAP_CONNECT_TIMEOUT = 5
# LDAP credentials, may both be None if anonymous access is enabled
LDAP_USER_DN = None
LDAP_PASSWORD = None

# OIDC settings
OIDC_NAME = None
OIDC_ISSUER = None
OIDC_CLIENT_ID = None
OIDC_CLIENT_SECRET = None
OIDC_SCOPES = 'openid profile email'
OIDC_DISABLE_NONCE = False
OIDC_ROLES = None
OIDC_ONLY = False
OIDC_CREATE_ACCOUNT = 'auto_link'
OIDC_ACCESS_TOKEN_AS_API_KEY = False
OIDC_ACCESS_TOKEN_ALLOW_INTROSPECTION = False

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
SERVICE_LEGAL_NOTICE = None
SERVICE_PRIVACY_POLICY = None
SERVICE_ACCESSIBILITY = None
HELP_URL = 'https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/#documentation'

# a map of file extensions and the MIME types they should be handled as
# this is used to determine which user uploaded files should be served as
# images (those with an image/ MIME type) in the object view and which support
# a preview.
# files with extensions not listed here only support being downloaded.
MIME_TYPES = {
    '.txt': 'text/plain',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
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

# Scicat settings
SCICAT_NAME = 'SciCat'
SCICAT_API_URL = None
SCICAT_FRONTEND_URL = None
SCICAT_EXTRA_PID_PREFIX = ''

DOWNLOAD_SERVICE_URL = None
DOWNLOAD_SERVICE_SECRET = None
DOWNLOAD_SERVICE_WHITELIST: typing.Dict[str, typing.List[int]] = {}
DOWNLOAD_SERVICE_TIME_LIMIT = 24 * 60 * 60

# PDF export settings
PDFEXPORT_LOGO_URL = None
PDFEXPORT_LOGO_ALIGNMENT = 'right'
PDFEXPORT_LOGO_WIDTH = 30

# label settings
LABEL_PAPER_FORMATS: list[dict[str, typing.Any]] = []

# CSRF token time limit
# users may take a long time to fill out a form during an experiment
WTF_CSRF_TIME_LIMIT = 12 * 60 * 60

# invitation link time limit
INVITATION_TIME_LIMIT = 7 * 24 * 60 * 60
DISABLE_USER_INVITATIONS = False

# Flask-MonitoringDashboard settings
ENABLE_MONITORINGDASHBOARD = False
MONITORINGDASHBOARD_DATABASE = 'sqlite:///flask_monitoringdashboard.db'

# other settings
ONLY_ADMINS_CAN_MANAGE_LOCATIONS = False
ONLY_ADMINS_CAN_CREATE_GROUPS = False
ONLY_ADMINS_CAN_DELETE_GROUPS = False
ONLY_ADMINS_CAN_CREATE_PROJECTS = False
ONLY_ADMINS_CAN_DELETE_PROJECTS = False
ONLY_ADMINS_CAN_MANAGE_GROUP_CATEGORIES = True

DISABLE_USE_IN_MEASUREMENT = False

DISABLE_SUBPROJECTS = False

USE_TYPEAHEAD_FOR_OBJECTS = False
TYPEAHEAD_OBJECT_LIMIT = None

ENFORCE_SPLIT_NAMES = False

BUILD_TRANSLATIONS = True
PYBABEL_PATH = 'pybabel'

EXTRA_USER_FIELDS: typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]] = {}

SHOW_PREVIEW_WARNING = False

DISABLE_INLINE_EDIT = False

SHOW_OBJECT_TITLE = False
WORKFLOW_VIEW_MODALS = False
WORKFLOW_VIEW_COLLAPSED = False

FULL_WIDTH_OBJECTS_TABLE = True

HIDE_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE = False

MAX_BATCH_SIZE = 100

FEDERATION_UUID = None
ENABLE_FEDERATION_DISCOVERABILITY = True
ALLOW_HTTP = False
VALID_TIME_DELTA = 300
ENABLE_DEFAULT_USER_ALIASES = False
ENABLE_FEDERATED_LOGIN = False
ENABLE_FEDERATED_LOGIN_CREATE_NEW_USER = False

ENABLE_WEBHOOKS_FOR_USERS = False
WEBHOOKS_ALLOW_HTTP = False

ENABLE_BACKGROUND_TASKS = False

TIMEZONE = None

ENABLE_ANONYMOUS_USERS = False

ENABLE_NUMERIC_TAGS = None

SHOW_UNHANDLED_OBJECT_RESPONSIBILITY_ASSIGNMENTS = True

SHOW_LAST_PROFILE_UPDATE = True

DISABLE_INSTRUMENTS = False

ENABLE_FUNCTION_CACHES = True

# temporary file time limit
TEMPORARY_FILE_TIME_LIMIT = 7 * 24 * 60 * 60

# CSP headers should be set, however this value can be used to disable them if necessary
ENABLE_CONTENT_SECURITY_POLICY = True

ENABLE_ELN_FILE_IMPORT = False
ELN_FILE_IMPORT_ALLOW_HTTP = False

ENABLE_FIDO2_PASSKEY_AUTHENTICATION = False

SHARED_DEVICE_SIGN_OUT_MINUTES = 30

DISABLE_OUTDATED_USE_AS_TEMPLATE = False

DISABLE_TOPICS = False

MIN_NUM_TEXT_CHOICES_FOR_SEARCH = 10

DEFAULT_NOTIFICATION_MODES = None

# environment variables override these values
use_environment_configuration(env_prefix='SAMPLEDB_')

if SERVICE_IMPRINT and not SERVICE_LEGAL_NOTICE:
    # Support SERVICE_IMPRINT for downwards compatibility
    SERVICE_LEGAL_NOTICE = SERVICE_IMPRINT

# remove trailing slashes from SciCat urls
if isinstance(SCICAT_API_URL, str) and SCICAT_API_URL.endswith('/'):
    SCICAT_API_URL = SCICAT_API_URL[:-1]  # pylint: disable=unsubscriptable-object
if isinstance(SCICAT_FRONTEND_URL, str) and SCICAT_FRONTEND_URL.endswith('/'):
    SCICAT_FRONTEND_URL = SCICAT_FRONTEND_URL[:-1]  # pylint: disable=unsubscriptable-object

# remove trailing slashes from Download Service url
if isinstance(DOWNLOAD_SERVICE_URL, str) and DOWNLOAD_SERVICE_URL.endswith('/'):
    DOWNLOAD_SERVICE_URL = DOWNLOAD_SERVICE_URL[:-1]  # pylint: disable=unsubscriptable-object

if OIDC_ONLY:
    DISABLE_INVITATIONS = True
