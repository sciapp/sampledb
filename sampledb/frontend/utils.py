# coding: utf-8
"""

"""

import json
import base64
import functools
import hashlib
import typing
from io import BytesIO
import os
from urllib.parse import quote_plus
from datetime import datetime
from math import log10, floor

import flask
import flask_babel
import flask_login
from flask_babel import format_datetime, format_date, get_locale
from babel import numbers
import qrcode
import qrcode.image.svg
import plotly
import pytz

from ..logic import errors
from ..logic.components import get_component_or_none
from ..logic.datatypes import Quantity
from ..logic.errors import UserIsReadonlyError
from ..logic.units import prettify_units
from ..logic.notifications import get_num_notifications
from ..logic.markdown_to_html import markdown_to_safe_html
from ..logic.users import get_user
from ..logic.utils import get_translated_text
from ..logic.schemas.conditions import are_conditions_fulfilled
from ..logic.settings import get_user_settings
from ..logic.action_permissions import get_sorted_actions_for_user
from ..logic.locations import Location, get_location
from ..logic.location_permissions import get_user_location_permissions, Permissions


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


def custom_format_datetime(
        utc_datetime: typing.Union[str, datetime],
        format: typing.Optional[str] = None
) -> str:
    """
    Returns a reformatted date in the given format.

    :param utc_datetime: a datetime string or object in UTC
    :param format: the target format or None for the user's medium-length format
    :return: the reformatted datetime or utc_datetime in case of an error
    """
    try:
        if not isinstance(utc_datetime, datetime):
            utc_datetime = parse_datetime_string(utc_datetime)
        if format is None:
            format2 = 'medium'
            return format_datetime(utc_datetime, format=format2)
        else:
            settings = get_user_settings(flask_login.current_user.id)
            utc_datetime = pytz.utc.localize(utc_datetime)
            local_datetime = utc_datetime.astimezone(pytz.timezone(settings['TIMEZONE']))
            return local_datetime.strftime(format)
    except ValueError:
        return utc_datetime


def custom_format_date(date, format='%Y-%m-%d'):
    if isinstance(date, datetime):
        datetime_obj = date
    else:
        datetime_obj = datetime.strptime(date, format)
    return format_date(datetime_obj)


def custom_format_number(number: typing.Union[str, int, float], display_digits: typing.Optional[int] = None) -> str:
    """
    Return the formatted number.

    :param number: either an int or a float, or a string representation of either
    :param display_digits: number of decimals to use, or None
    :return: the formatted number
    """
    try:
        # if number is a string that can not be formatted. Wrong inputs...
        number = float(number)
    except ValueError:
        return number
    if type(display_digits) is not int:
        display_digits = None
    else:
        # there cannot be a negative number of digits
        if display_digits < 0:
            display_digits = 0

        # explicitly round the number, as that might change the exponent
        number = round(number, display_digits)

    locale = get_locale()
    if number == 0:
        exponent = 0
    else:
        exponent = int(floor(log10(abs(number))))

    # for very small or very large absolute numbers, the exponential format should be used
    use_exponential_format = not -5 < exponent < 6

    format = None
    if display_digits is not None:
        if use_exponential_format:
            display_digits += exponent

        if display_digits < 0:
            display_digits = 0
        if display_digits > 27:
            display_digits = 27

        positive_format = '0.' + '0' * display_digits
        if use_exponential_format:
            # including E will enable exponential format, 0 means the exponent should be shown even if 0
            positive_format += 'E0'
        negative_format = '-' + positive_format
        format = positive_format + ';' + negative_format

    if use_exponential_format:
        return numbers.format_scientific(
            number,
            locale=locale,
            format=format,
            decimal_quantization=False
        )
    else:
        with numbers.decimal.localcontext() as ctx:
            ctx.prec = 15
            return numbers.format_decimal(
                numbers.decimal.Decimal(number),
                locale=locale,
                format=format,
                decimal_quantization=False,
                group_separator=False
            )


def custom_format_quantity(
        data: typing.Optional[typing.Dict[str, typing.Any]],
        schema: typing.Dict[str, typing.Any]
) -> str:
    if data is None:
        mdash = '\u2014'
        return mdash
    if schema.get('units', '1') == '1':
        return custom_format_number(data.get('magnitude_in_base_units', 0), schema.get('display_digits', None))
    quantity = Quantity.from_json(data)
    narrow_non_breaking_space = '\u202f'
    return custom_format_number(quantity.magnitude, schema.get('display_digits', None)) + narrow_non_breaking_space + prettify_units(quantity.units)


@jinja_filter
def parse_datetime_string(datetime_string):
    return datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S')


@jinja_filter
def default_format_datetime(utc_datetime: typing.Union[str, datetime]) -> str:
    return custom_format_datetime(utc_datetime, format='%Y-%m-%d %H:%M:%S')


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


def get_location_name(
        location_or_location_id: typing.Union[int, Location],
        include_id: bool = False,
        language_code: typing.Optional[str] = None
) -> str:
    location: typing.Optional[Location]
    location_id: int
    if type(location_or_location_id) is int:
        location_id = location_or_location_id
        try:
            location = get_location(location_id)
        except errors.LocationDoesNotExistError:
            location = None
    elif isinstance(location_or_location_id, Location):
        location = location_or_location_id
        location_id = location.id
    else:
        return flask_babel.gettext("Unknown Location")

    if location is None or Permissions.READ not in get_user_location_permissions(location_id, flask_login.current_user.id):
        # location ID is always included when the location cannot be accessed
        location_name = flask_babel.gettext("Location") + f' #{location_id}'
    else:
        location_name = get_translated_text(
            location.name,
            language_code=language_code,
            default=flask_babel.gettext('Unnamed Location')
        )
        if include_id:
            location_name += f' (#{location_id})'
    return location_name


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
_jinja_filters['format_quantity'] = custom_format_quantity
_jinja_filters['base64encode'] = base64encode
_jinja_filters['are_conditions_fulfilled'] = filter_are_conditions_fulfilled
_jinja_filters['to_string_if_dict'] = to_string_if_dict
_jinja_filters['get_location_name'] = get_location_name


def get_style_aliases(style):
    return {
        'horizontal_table': ['table', 'horizontal_table']
    }.get(style, [style])


def get_template(template_folder, default_prefix, schema):
    system_path = os.path.join(os.path.dirname(__file__), 'templates', template_folder)
    base_file = schema["type"] + ".html"

    file_order = [(default_prefix + base_file)]
    if schema.get('parent_style'):
        for parent_style in get_style_aliases(schema['parent_style']):
            file_order.insert(0, (default_prefix + parent_style + "_" + base_file))
    if schema.get('style'):
        for style in get_style_aliases(schema['style']):
            file_order.insert(0, (default_prefix + style + "_" + base_file))
    if schema.get('parent_style') and schema.get('style'):
        for style in get_style_aliases(schema['style']):
            for parent_style in get_style_aliases(schema['parent_style']):
                file_order.insert(0, (default_prefix + parent_style + "_" + style + "_" + base_file))

    for file in file_order:
        if os.path.exists(os.path.join(system_path, file)):
            return template_folder + file

    return template_folder + default_prefix + base_file


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


def get_templates(user_id):
    return [
        action
        for action in get_sorted_actions_for_user(user_id=user_id)
        if action.type.is_template
    ]


def get_user_if_exists(user_id: int, component_id: typing.Optional[int] = None):
    try:
        return get_user(user_id, component_id)
    except errors.UserDoesNotExistError:
        return None
    except errors.ComponentDoesNotExistError:
        return None


_application_root_url: typing.Optional[str] = None


def relative_url_for(route: str, **kwargs) -> str:
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


@functools.lru_cache(maxsize=None)
def get_fingerprint(file_path: str) -> str:
    """
    Calculate a fingerprint for a given file.

    :param file_path: path to the file that should be fingerprinted
    :return: the file fingerprint, or an empty string
    """
    try:
        block_size = 65536
        hash_method = hashlib.md5()
        with open(file_path, 'rb') as input_file:
            buf = input_file.read(block_size)
            while buf:
                hash_method.update(buf)
                buf = input_file.read(block_size)
        return hash_method.hexdigest()
    except Exception:
        # if the file cannot be hashed for any reason, return an empty fingerprint
        return ''


STATIC_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))


def fingerprinted_static(filename: str) -> str:
    return flask.url_for(
        'static',
        filename=filename,
        v=get_fingerprint(os.path.join(STATIC_DIRECTORY, filename))
    )


_jinja_functions = {}
_jinja_functions['get_view_template'] = get_view_template
_jinja_functions['get_form_template'] = get_form_template
_jinja_functions['get_local_month_names'] = get_local_month_names
_jinja_functions['get_inline_edit_template'] = get_inline_edit_template
_jinja_functions['get_templates'] = get_templates
_jinja_functions['get_component_or_none'] = get_component_or_none
_jinja_functions['relative_url_for'] = relative_url_for
_jinja_functions['fingerprinted_static'] = fingerprinted_static
