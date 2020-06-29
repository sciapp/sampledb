# coding: utf-8
"""

"""

import base64
from io import BytesIO
import os
from urllib.parse import quote_plus

import bleach
import flask
import flask_login
import markdown
import qrcode
import qrcode.image.svg

from ..logic.errors import UserIsReadonlyError
from ..logic.units import prettify_units
from ..logic.notifications import get_num_notifications


def jinja_filter(func):
    global _jinja_filters
    _jinja_filters[func.__name__] = func
    return func


_jinja_filters = {}
jinja_filter.filters = _jinja_filters


qrcode_cache = {}


def generate_qrcode(url: str, should_cache: bool = True) -> str:
    """
    Generate a QR code (as data URI) to a given URL.

    :param url: the url the QR code should reference
    :param should_cache: whether or not the QR code should be cached
    :return: a data URI to a base64 encoded SVG image
    """
    if should_cache and url in qrcode_cache:
        return qrcode_cache[url]
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathFillImage)
    image_stream = BytesIO()
    image.save(image_stream)
    image_stream.seek(0)
    qrcode_url = 'data:image/svg+xml;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')
    if should_cache:
        qrcode_cache[url] = qrcode_url
    return qrcode_url


def markdown_to_safe_html(markdown_text):
    return markdown.markdown(
        bleach.clean(markdown_text),
        extensions=['tables']
    )


def has_preview(file):
    if file.storage != 'local':
        return False
    file_name = file.original_file_name
    file_extension = os.path.splitext(file_name)[1]
    return file_extension in flask.current_app.config.get('MIME_TYPES', {})


def file_name_is_image(file_name):
    file_extension = os.path.splitext(file_name)[1]
    return flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, '').startswith('image/')


def is_image(file):
    if file.storage != 'local':
        return False
    return file_name_is_image(file.original_file_name)


def attachment_is_image(file_attachment):
    return file_name_is_image(file_attachment.file_name)


def get_num_unread_notifications(user):
    return get_num_notifications(user.id, unread_only=True)


def check_current_user_is_not_readonly():
    if flask_login.current_user.is_readonly:
        raise UserIsReadonlyError()


_jinja_filters['prettify_units'] = prettify_units
_jinja_filters['has_preview'] = has_preview
_jinja_filters['is_image'] = is_image
_jinja_filters['attachment_is_image'] = attachment_is_image
_jinja_filters['get_num_unread_notifications'] = get_num_unread_notifications
_jinja_filters['urlencode'] = quote_plus
