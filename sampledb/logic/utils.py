# coding: utf-8
"""

"""
import datetime
import functools
import re
import typing
import sys

import flask
import pytz
from flask_login import current_user

from . import errors
from .. import db
from .background_tasks.send_mail import post_send_mail_task
from .security_tokens import generate_token
from ..models import Authentication, AuthenticationType, User, Tag, BackgroundTaskStatus, BackgroundTask, UserType
from ..utils import ansi_color


def send_user_invitation_email(
        email: str,
        invitation_id: int
) -> BackgroundTaskStatus:
    token_data = {
        'email': email,
        'invitation_id': invitation_id
    }
    token = generate_token(
        token_data,
        salt='invitation',
        secret_key=flask.current_app.config['SECRET_KEY']
    )
    confirm_url = flask.url_for('frontend.invitation_route', token=token, _external=True)

    service_name = flask.current_app.config['SERVICE_NAME']
    subject = service_name + " Invitation"
    html = flask.render_template('mails/user_invitation.html', confirm_url=confirm_url)
    text = flask.render_template('mails/user_invitation.txt', confirm_url=confirm_url)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    return post_send_mail_task(
        subject=subject,
        recipients=[email],
        text=text,
        html=html
    )[0]


def send_email_confirmation_email(
        email: str,
        user_id: int,
        salt: str
) -> typing.Tuple[BackgroundTaskStatus, typing.Optional[BackgroundTask]]:
    token_data = {
        'email': email,
        'user_id': user_id
    }
    token = generate_token(
        token_data,
        salt=salt,
        secret_key=flask.current_app.config['SECRET_KEY']
    )
    confirm_url = flask.url_for("frontend.user_preferences", user_id=user_id, token=token, _external=True)

    service_name = flask.current_app.config['SERVICE_NAME']
    subject = service_name + " Email Confirmation"
    html = flask.render_template('mails/email_confirmation.html', confirm_url=confirm_url)
    text = flask.render_template('mails/email_confirmation.txt', confirm_url=confirm_url)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    return post_send_mail_task(
        subject=subject,
        recipients=[email],
        text=text,
        html=html
    )


def send_recovery_email(
        email: str
) -> typing.Optional[typing.Tuple[BackgroundTaskStatus, typing.Optional[BackgroundTask]]]:
    users = User.query.filter_by(email=email).all()
    email_authentication = Authentication.query.filter(db.and_(Authentication.login['login'].astext == email, Authentication.type == AuthenticationType.EMAIL)).first()
    if email_authentication is not None and email_authentication.user not in users:
        users.append(email_authentication.user)

    # do not provide password resets for users from other databases
    users = [
        user
        for user in users
        if user.type != UserType.FEDERATION_USER
    ]

    if not users:
        return None

    password_reset_urls = {}
    for user in users:
        for authentication_method in user.authentication_methods:
            if authentication_method.type not in {AuthenticationType.LDAP, AuthenticationType.API_TOKEN, AuthenticationType.API_ACCESS_TOKEN}:
                password_reset_urls[authentication_method] = build_confirm_url(authentication_method)

    def filter_printable_authentication_methods(authentication_methods: typing.Iterable[Authentication]) -> typing.List[Authentication]:
        printable_authentication_methods = []
        for authentication_method in authentication_methods:
            if authentication_method.type in {AuthenticationType.LDAP, AuthenticationType.EMAIL, AuthenticationType.OTHER}:
                printable_authentication_methods.append(authentication_method)
        return printable_authentication_methods

    service_name = flask.current_app.config['SERVICE_NAME']
    subject = service_name + " Account Recovery"
    html = flask.render_template('mails/account_recovery.html', email=email, users=users, password_reset_urls=password_reset_urls, filter_printable_authentication_methods=filter_printable_authentication_methods)
    text = flask.render_template('mails/account_recovery.txt', email=email, users=users, password_reset_urls=password_reset_urls, filter_printable_authentication_methods=filter_printable_authentication_methods)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    return post_send_mail_task(
        subject=subject,
        recipients=[email],
        text=text,
        html=html
    )


def send_federated_login_account_creation_email(
    email: str,
    username: str,
    component_id: int,
    fed_id: int
) -> typing.Tuple[BackgroundTaskStatus, typing.Optional[BackgroundTask]]:
    token_data = {
        'email': email,
        'username': username,
        'component_id': component_id,
        'fed_id': fed_id
    }
    token = generate_token(
        token_data,
        salt='federated_login_account',
        secret_key=flask.current_app.config['SECRET_KEY']
    )

    service_name = flask.current_app.config['SERVICE_NAME']
    subject = f"{service_name} Account Creation"
    confirm_url = flask.url_for('.create_account_by_federated_login', token=token, _external=True)

    text = flask.render_template(
        "mails/federated_login_account_creation.txt",
        confirm_url=confirm_url,
        username=token_data['username'],
        service_name=service_name
    )
    html = flask.render_template(
        "mails/federated_login_account_creation.html",
        confirm_url=confirm_url,
        username=token_data['username'],
        service_name=service_name
    )

    return post_send_mail_task(
        subject=subject,
        recipients=[email],
        text=text,
        html=html
    )


def build_confirm_url(
        authentication_method: Authentication,
        salt: str = 'password'
) -> str:
    assert authentication_method.type != AuthenticationType.LDAP

    user_id = authentication_method.user_id
    token = generate_token(authentication_method.id, salt=salt,
                           secret_key=flask.current_app.config['SECRET_KEY'])
    return str(flask.url_for("frontend.user_preferences", user_id=user_id, token=token, _external=True))


def get_translated_text(
        text: typing.Optional[typing.Union[str, typing.Dict[str, str]]],
        language_code: typing.Optional[str] = None,
        default: str = ''
) -> str:
    """
    Return the text in a given language from a translation dictionary.

    If the language does not exist in text, the return value will fall back to
    the english text if it does exist or to an empty string otherwise.

    If text is a string instead of a dict, it will be returned as-is.

    If no language code is provided, the current user's language will be used.

    :param text: a dict mapping language codes to translations
    :param language_code: a language code, or None
    :param default: a text to return if the input text is None or empty
    :return: the translation
    """
    # late import to avoid circular imports
    from .languages import get_user_language
    if isinstance(text, str):
        return text

    if isinstance(text, dict):
        if language_code is None:
            language_code = get_user_language(current_user).lang_code
        translated_text = text.get(language_code)
        if translated_text:
            return translated_text
        # fall back to english
        translated_text = text.get('en')
        if translated_text:
            return translated_text
        # fall back to first language code with non-empty content
        for fallback_language_code in sorted(text):
            translated_text = text[fallback_language_code]
            if translated_text:
                return translated_text

    return default


def get_all_translated_texts(
        text: typing.Optional[typing.Union[str, typing.Dict[str, str]]],
        join_symbol: str,
        default: str = ''
) -> str:
    """
    Return all translations from a translation dictionary.

    The english translation will always be first in the result, if it exists.

    If text is a string instead of a dict, it will be returned as-is.

    If text is neither a string nor a dict, a default will be returned.

    :param text: a dict mapping language codes to translations
    :param join_symbol: the symbol to join translations with
    :param default: a text to return if the input text is None or empty
    :return: the translation
    """
    if isinstance(text, str):
        return text

    if isinstance(text, dict):
        translations = []
        if 'en' in text:
            translations.append(text['en'])
        for language_code, translation in text.items():
            if language_code != 'en':
                translations.append(translation)
        return join_symbol.join(translations)

    return default


def parse_url(
        url: str,
        max_length: int = 2048,
        valid_schemes: typing.Sequence[str] = ('http', 'https', 'ftp', 'file', 'sftp', 'smb')
) -> typing.Dict[str, str]:
    """
    Validate and parse a given URI/URL.

    In case of file-URIs a hostname is required, so local references
    like file:///path and file:/path are considered invalid.

    :param url: string representing the URI to validate
    :param max_length: the URI strings maximum allowed length (default: 2048)
    :param valid_schemes: valid URI schemes
    :return: a dict containing scheme, domain, host, ip_address, port, path and query of the given URI
    :raise errors.InvalidURLError: if the given URL is invalid
    :raise errors.URLTooLongError: if the given URL is too long
    :raise errors.InvalidIPAddressError: if the IP contained in the given URL
        is invalid
    :raise errors.InvalidPortNumberError: if the port contained in the given
        URL is invalid
    """
    if not len(url) <= max_length:
        raise errors.URLTooLongError()

    regex = re.compile(
        # schemes
        r'^(?P<scheme>' + r'|'.join(valid_schemes) + r')://'
        # IP address and port
        r'(?:(?P<ip_address>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})|'
        # IP address and port
        r'\[(?P<ipv6_address>'
        r'[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){7}|'
        r'(?:[0-9a-fA-F]{1,4}:){1,7}:|'
        r'(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]|'
        r'(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|'
        r'(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|'
        r'(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|'
        r'(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|'
        r'[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}|'
        r':(?::[0-9a-fA-F]{1,4}){1,7}'
        r')]|'
        # fqdn
        r'(?P<domain>(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9]{2,}\.?))|'
        # hostname
        r'(?P<host>[A-Z0-9-]+))'
        # port
        r'(?::(?P<port>\d+))?'
        # path
        r'(?P<path>/?|[/?]\S+)'
        # query
        r'(?P<query>\?\S*)?$', re.IGNORECASE)
    match = re.match(regex, url)

    if match is None:
        raise errors.InvalidURLError()

    match_dict = match.groupdict()
    if match_dict['ip_address']:
        for block in match_dict['ip_address'].split('.'):
            num = int(block)
            if num < 0 or num > 225:
                raise errors.InvalidIPAddressError()

    if match_dict['port']:
        num = int(match_dict['port'])
        if num < 1 or num > 65535:
            raise errors.InvalidPortNumberError()

    return match_dict


def print_deprecation_warnings() -> None:
    if show_numeric_tags_warning():
        print(
            ansi_color(
                "Numeric tags are enabled, please evaluate if these are "
                "necessary for your use case and set the configuration value "
                "ENABLE_NUMERIC_TAGS to False to disable them. To learn more,"
                "see: "
                "https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/deprecated_features.html#numeric-tags",
                color=33
            ),
            file=sys.stderr,
            end='\n\n'
        )


def show_numeric_tags_warning() -> bool:
    return bool(flask.current_app.config['ENABLE_NUMERIC_TAGS'])


def do_numeric_tags_exist() -> bool:
    """
    Return whether any numeric tags exist in the tags table.

    :return: whether any numeric tags exist
    """
    return Tag.query.filter(Tag.name.op("~")(r'^[0-9\.]+$')).first() is not None


_T = typing.TypeVar('_T')
_CACHE_FUNCTIONS: typing.Set[typing.Callable[..., _T]] = set()


def cache(function: typing.Callable[..., _T]) -> typing.Callable[..., _T]:
    """
    Decorator for adding caching to functions via functools.cache().

    Functions with this decorator can have their cache cleared via the
    clear_cache_functions function.

    :param function: the function to decorate
    :return: the decorated function
    """
    # this decorator will be used before the app is created, so the config
    # variable has to be used directly instead of via flask.current_app.config
    from ..config import ENABLE_FUNCTION_CACHES
    if not ENABLE_FUNCTION_CACHES:
        return function
    cache_function = functools.cache(function)
    _CACHE_FUNCTIONS.add(cache_function)  # type: ignore
    return cache_function


def clear_cache_functions() -> None:
    """
    Clear the cache of all functions decorated with the cache decorator.
    """
    for cache_function in _CACHE_FUNCTIONS:
        cache_function.cache_clear()  # type: ignore


def get_data_and_schema_by_id_path(
        data: typing.Optional[typing.Union[typing.List[typing.Any], typing.Dict[str, typing.Any]]],
        schema: typing.Optional[typing.Dict[str, typing.Any]],
        id_path: typing.List[typing.Union[str, int]],
        convert_id_path_elements: bool = False
) -> typing.Optional[typing.Tuple[typing.Union[typing.List[typing.Any], typing.Dict[str, typing.Any]], typing.Dict[str, typing.Any]]]:
    if data is None or schema is None:
        return None
    if not id_path:
        return data, schema
    if schema.get('type') == 'array':
        if not isinstance(data, list):
            return None
        if not isinstance(id_path[0], int) and convert_id_path_elements:
            try:
                id_path[0] = int(id_path[0])
            except ValueError:
                return None
        if not isinstance(id_path[0], int):
            return None
        if id_path[0] < 0 or id_path[0] >= len(data):
            return None
        return get_data_and_schema_by_id_path(data[id_path[0]], schema['items'], id_path[1:], convert_id_path_elements=convert_id_path_elements)
    if schema.get('type') == 'object':
        if not isinstance(data, dict):
            return None
        if not isinstance(id_path[0], str) and convert_id_path_elements:
            id_path[0] = str(id_path[0])
        if not isinstance(id_path[0], str):
            return None
        if id_path[0] not in schema['properties']:
            return None
        if id_path[0] not in data:
            return None
        return get_data_and_schema_by_id_path(data[id_path[0]], schema['properties'][id_path[0]], id_path[1:], convert_id_path_elements=convert_id_path_elements)
    return None


_application_root_url: typing.Optional[str] = None


def relative_url_for(
        route: str,
        **kwargs: typing.Any
) -> str:
    global _application_root_url
    if _application_root_url is None:
        _application_root_url = flask.url_for('frontend.index')
    kwargs['_external'] = False
    url = flask.url_for(route, **kwargs)
    if url.startswith(_application_root_url):
        url = url[len(_application_root_url):]
    elif url.startswith('/'):
        url = url[1:]
    return url


@functools.cache
def get_postgres_timezone_alias(timezone_name: str, reference_date: datetime.date) -> str:
    current_utc_offset = pytz.timezone(timezone_name).utcoffset(datetime.datetime.now())
    timezone_names_table = db.table(
        'pg_timezone_names',
        db.Column('name', db.String),
        db.Column('utc_offset', db.Interval)
    )
    stmt = db.select(db.exists().where(db.and_(
        timezone_names_table.columns.name == timezone_name,
        timezone_names_table.columns.utc_offset == current_utc_offset
    )))
    if db.session.scalar(stmt):
        return timezone_name
    # create offset-based timezone as a fallback, if timezone data for postgres is out of date or incomplete
    reference_datetime = datetime.datetime(reference_date.year, reference_date.month, reference_date.day)
    naive_reference_datetime = reference_datetime.replace(tzinfo=None)
    reference_utc_offset = pytz.timezone(timezone_name).utcoffset(naive_reference_datetime)
    current_timezone = datetime.timezone(reference_utc_offset)
    current_timezone_name = current_timezone.tzname(naive_reference_datetime)
    # convert from ISO notation to POSIX notation
    if '+' in current_timezone_name:
        current_timezone_name = current_timezone_name.replace('+', '-')
    elif '-' in current_timezone_name:
        current_timezone_name = current_timezone_name.replace('-', '+')
    return current_timezone_name
