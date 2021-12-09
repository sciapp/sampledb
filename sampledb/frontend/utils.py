# coding: utf-8
"""

"""

import json
import base64
from io import BytesIO
import os
from urllib.parse import quote_plus
from datetime import datetime
from math import log10

import flask
import flask_babel
import flask_login
from flask_babel import format_number, format_datetime, format_date, format_decimal, format_scientific
import qrcode
import qrcode.image.svg
import plotly
import pytz

from ..logic.errors import UserIsReadonlyError
from ..logic.units import prettify_units
from ..logic.notifications import get_num_notifications
from ..logic.markdown_to_html import markdown_to_safe_html
from ..logic.utils import get_translated_text
from ..logic.schemas.conditions import are_conditions_fulfilled
from ..logic.settings import get_user_settings


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


def has_preview(file):
    if file.storage not in {'local', 'database'}:
        return False
    file_name = file.original_file_name
    file_extension = os.path.splitext(file_name)[1]
    return file_extension in flask.current_app.config.get('MIME_TYPES', {})


def file_name_is_image(file_name):
    file_extension = os.path.splitext(file_name)[1]
    return flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, '').startswith('image/')


def is_image(file):
    if file.storage not in {'local', 'database'}:
        return False
    return file_name_is_image(file.original_file_name)


def attachment_is_image(file_attachment):
    return file_name_is_image(file_attachment.file_name)


def get_num_unread_notifications(user):
    return get_num_notifications(user.id, unread_only=True)


def check_current_user_is_not_readonly():
    if flask_login.current_user.is_readonly:
        raise UserIsReadonlyError()


def generate_jinja_hash(object):
    return hash(object)


def plotly_base64_image_from_json(object):
    try:
        fig_plot = plotly.io.from_json(json.dumps(object))
    except ValueError:
        return
    image_stream = BytesIO()
    fig_plot.write_image(image_stream, "svg")
    image_stream.seek(0)
    return 'data:image/svg+xml;base64,{}'.format(base64.b64encode(image_stream.read()).decode('utf-8'))


def plotly_chart_get_title(plotly_object):
    layout = plotly_object.get('layout')
    if isinstance(layout, dict):
        title = layout.get('title')
        if isinstance(title, str):
            return title
        if isinstance(title, dict):
            text = title.get('text')
            if isinstance(text, str):
                return text
    return ""


def to_json_no_extra_escapes(json_object, indent=None):
    return json.dumps(json_object, indent=indent)


def custom_format_datetime(date, format='%Y-%m-%d %H:%M:%S'):
    """
    Returns a reformatted date in the given format.

    :param date: a string representing a date in the given format
    :param format: a string for the format of the given date
    :return: the reformatted date or in case of an error the input date
    """
    try:
        if isinstance(date, datetime):
            datetime_obj = date
        else:
            datetime_obj = datetime.strptime(date, format)
        if format == '%Y-%m-%d %H:%M:%S':
            format2 = 'medium'
            return format_datetime(datetime_obj, format=format2)
        else:
            return format_date(datetime_obj.date())
    except ValueError:
        return date


def custom_format_date(date, format='%Y-%m-%d'):
    if isinstance(date, datetime):
        datetime_obj = date
    else:
        datetime_obj = datetime.strptime(date, format)
    return format_date(datetime_obj)


def custom_format_number(number):
    """
    Return the formatted number.

    :param number: either an int or a float
    :return: the reformatted number
    """
    try:
        # if number is a string that can not be formatted. Wrong inputs...
        float(number)
    except ValueError:
        return number
    if float(number) != 0:
        if log10(abs(float(number))) <= -5.0 or int(log10(abs(float(number)))) >= 6:
            return format_scientific(number)
    if type(number) is int:
        return format_number(number)
    return format_decimal(number)


@jinja_filter
def parse_datetime_string(datetime_string):
    return datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S')


@jinja_filter
def default_format_datetime(utc_datetime):
    settings = get_user_settings(flask_login.current_user.id)
    utc_datetime = pytz.utc.localize(utc_datetime)
    local_datetime = utc_datetime.astimezone(pytz.timezone(settings['TIMEZONE']))
    return local_datetime.strftime('%Y-%m-%d %H:%M:%S')


@jinja_filter
def convert_datetime_input(datetime_input):
    if not datetime_input:
        return ''
    try:
        local_datetime = datetime.strptime(datetime_input, flask_login.current_user.language.datetime_format_datetime)
        return local_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return ''


def base64encode(value):
    return base64.b64encode(json.dumps(value).encode('utf8')).decode('ascii')


def filter_are_conditions_fulfilled(data, property_schema) -> bool:
    if not data:
        return False
    if not isinstance(property_schema, dict):
        return False
    return are_conditions_fulfilled(property_schema.get('conditions'), data)


def to_string_if_dict(data) -> str:
    if isinstance(data, dict):
        return str(data)
    else:
        return data


_jinja_filters['prettify_units'] = prettify_units
_jinja_filters['has_preview'] = has_preview
_jinja_filters['is_image'] = is_image
_jinja_filters['attachment_is_image'] = attachment_is_image
_jinja_filters['get_num_unread_notifications'] = get_num_unread_notifications
_jinja_filters['urlencode'] = quote_plus
_jinja_filters['markdown_to_safe_html'] = markdown_to_safe_html
_jinja_filters['hash'] = generate_jinja_hash
_jinja_filters['plot'] = plotly_base64_image_from_json
_jinja_filters['plotly_chart_get_title'] = plotly_chart_get_title
_jinja_filters['to_json_no_extra_escapes'] = to_json_no_extra_escapes
_jinja_filters['get_translated_text'] = get_translated_text
_jinja_filters['babel_format_datetime'] = custom_format_datetime
_jinja_filters['babel_format_date'] = custom_format_date
_jinja_filters['babel_format_number'] = custom_format_number
_jinja_filters['base64encode'] = base64encode
_jinja_filters['are_conditions_fulfilled'] = filter_are_conditions_fulfilled
_jinja_filters['to_string_if_dict'] = to_string_if_dict


def get_template(template_folder, default_prefix, schema):
    system_path = os.path.join(os.path.dirname(__file__), 'templates', template_folder)
    base_file = schema["type"] + ".html"

    file_order = [(default_prefix + base_file)]
    if schema.get('parent_style'):
        file_order.insert(0, (default_prefix + schema["parent_style"] + "_" + base_file))
    if schema.get('style'):
        file_order.insert(0, (default_prefix + schema["style"] + "_" + base_file))
    if schema.get('parent_style') and schema.get('style'):
        file_order.insert(0, (default_prefix + schema["parent_style"] + "_" + schema.get('style') + "_" + base_file))

    for file in file_order:
        if os.path.exists(os.path.join(system_path, file)):
            return (template_folder + file)

    return (template_folder + default_prefix + base_file)


def get_form_template(schema):
    return get_template('objects/forms/', 'form_', schema)


def get_view_template(schema):
    return get_template('objects/view/', '', schema)


def get_inline_edit_template(schema):
    return get_template('objects/inline_edit/', 'inline_edit_', schema)


def get_local_month_names():
    return [
        flask_babel.get_locale().months['format']['wide'][i]
        for i in range(1, 13)
    ]


_jinja_functions = {}
_jinja_functions['get_view_template'] = get_view_template
_jinja_functions['get_form_template'] = get_form_template
_jinja_functions['get_local_month_names'] = get_local_month_names
_jinja_functions['get_inline_edit_template'] = get_inline_edit_template
