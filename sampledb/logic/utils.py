# coding: utf-8
"""

"""

import re
import typing
import sys

import flask
import flask_login

from . import errors
from .languages import get_user_language
from .. import db
from .background_tasks.send_mail import post_send_mail_task, BackgroundTaskStatus
from .security_tokens import generate_token
from ..models import Authentication, AuthenticationType, User, File
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


def send_email_confirmation_email(email, user_id, salt):
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


def send_recovery_email(email):
    users = User.query.filter_by(email=email).all()
    email_authentication = Authentication.query.filter(db.and_(Authentication.login['login'].astext == email, Authentication.type == AuthenticationType.EMAIL)).first()
    if email_authentication is not None and email_authentication.user not in users:
        users.append(email_authentication.user)

    if not users:
        return

    password_reset_urls = {}
    for user in users:
        for authentication_method in user.authentication_methods:
            if authentication_method.type not in {AuthenticationType.LDAP, AuthenticationType.API_TOKEN}:
                password_reset_urls[authentication_method] = build_confirm_url(authentication_method)

    def filter_printable_authentication_methods(authentication_methods):
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


def build_confirm_url(authentication_method, salt='password'):
    assert authentication_method.type != AuthenticationType.LDAP

    user_id = authentication_method.user_id
    token = generate_token(authentication_method.id, salt=salt,
                           secret_key=flask.current_app.config['SECRET_KEY'])
    return flask.url_for("frontend.user_preferences", user_id=user_id, token=token, _external=True)


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

    if language_code is None:
        language_code = get_user_language(flask_login.current_user).lang_code

    if isinstance(text, str):
        return text

    if isinstance(text, dict):
        return str(text.get(language_code, text.get('en', default)))

    return default


def parse_url(url, max_length=100, valid_schemes=['http', 'https', 'ftp', 'file', 'sftp', 'smb']):
    """
    Validate and parse a given URI/URL.

    In case of file-URIs a hostname is required, so local references
    like file:///path and file:/path are considered invalid.

    :param url: string representing the URI to validate
    :param max_length: the URI strings maximum allowed length.
    :param valid_schemes: valid URI schemes
    :return: a dict containing scheme, domain, host, ip_address, port, path and query of the given URI
    :raises: InvalidURIError if the given URI is invalid
    """
    if not 1 <= len(url) <= max_length:
        raise errors.InvalidURLError()

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
                raise errors.InvalidURLError()

    if match_dict['port']:
        num = int(match_dict['port'])
        if num < 1 or num > 65535:
            raise errors.InvalidURLError()

    return match_dict


def print_deprecation_warnings() -> None:
    if show_admin_local_storage_warning():
        print(
            ansi_color(
                "Some objects have files in 'local' storage, please move them "
                "to 'database' storage. To learn more, see: "
                "https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/deprecated_features.html#local-file-storage",
                color=33
            ),
            file=sys.stderr,
            end='\n\n'
        )
    if show_load_objects_in_background_warning():
        print(
            ansi_color(
                "Asynchronous loading of object lists is disabled, please do "
                "not set the configuration value 'LOAD_OBJECTS_IN_BACKGROUND' "
                "or set it to 'True' or '1'. To learn more, see: "
                "https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/deprecated_features.html#synchronous-loading-of-object Lists",
                color=33
            ),
            file=sys.stderr,
            end='\n\n'
        )


def show_admin_local_storage_warning() -> bool:
    return File.query.filter(db.text("data->>'storage' = 'local'")).first() is not None


def show_load_objects_in_background_warning() -> bool:
    return not flask.current_app.config['LOAD_OBJECTS_IN_BACKGROUND']
