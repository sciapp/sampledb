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
from ..logic.components import get_component_or_none, get_component, get_component_by_uuid
from ..logic.datatypes import Quantity
from ..logic.errors import UserIsReadonlyError
from ..logic.units import prettify_units
from ..logic.notifications import get_num_notifications
from ..logic.markdown_to_html import markdown_to_safe_html
from ..logic.users import get_user
from ..logic.utils import get_translated_text, get_all_translated_texts, show_admin_local_storage_warning, show_load_objects_in_background_warning
from ..logic.schemas.conditions import are_conditions_fulfilled
from ..logic.schemas.utils import get_property_paths_for_schema
from ..logic.action_permissions import get_sorted_actions_for_user
from ..logic.locations import Location, get_location
from ..logic.location_permissions import get_user_location_permissions, Permissions
from ..logic.datatypes import JSONEncoder


def jinja_filter(name: str = ''):
    def decorator(func, name):
        if not name:
            name = func.__name__
        jinja_filter.filters[name] = func
        return func

    return lambda func: decorator(func, name)


def jinja_function(name: str = ''):
    def decorator(func, name):
        if not name:
            name = func.__name__
        jinja_function.functions[name] = func
        return func

    return lambda func: decorator(func, name)


jinja_filter.filters = {}
jinja_filter()(hash)
jinja_filter()(prettify_units)
jinja_filter('urlencode')(quote_plus)
jinja_filter()(markdown_to_safe_html)
jinja_filter()(get_translated_text)
jinja_filter()(get_all_translated_texts)

jinja_function.functions = {}
jinja_function()(get_component_or_none)


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


@jinja_filter()
def has_preview(file):
    if file.storage not in {'local', 'database'}:
        return False
    file_name = file.original_file_name
    file_extension = os.path.splitext(file_name)[1]
    return file_extension in flask.current_app.config.get('MIME_TYPES', {})


def file_name_is_image(file_name):
    file_extension = os.path.splitext(file_name)[1]
    return flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, '').startswith('image/')


@jinja_filter()
def is_image(file):
    if file.storage not in {'local', 'database'}:
        return False
    return file_name_is_image(file.original_file_name)


@jinja_filter()
def attachment_is_image(file_attachment):
    return file_name_is_image(file_attachment.file_name)


@jinja_filter()
def get_num_unread_notifications(user):
    return get_num_notifications(user.id, unread_only=True)


def check_current_user_is_not_readonly():
    if flask_login.current_user.is_readonly:
        raise UserIsReadonlyError()


@jinja_filter('plot')
def plotly_base64_image_from_json(object):
    try:
        fig_plot = plotly.io.from_json(json.dumps(object))
    except ValueError:
        return
    image_stream = BytesIO()
    fig_plot.write_image(image_stream, "svg")
    image_stream.seek(0)
    return 'data:image/svg+xml;base64,{}'.format(base64.b64encode(image_stream.read()).decode('utf-8'))


@jinja_filter()
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


@jinja_filter()
def to_json_no_extra_escapes(json_object, indent=None):
    return json.dumps(json_object, indent=indent)


@jinja_filter('babel_format_datetime')
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
            utc_datetime = pytz.utc.localize(utc_datetime)
            local_datetime = utc_datetime.astimezone(pytz.timezone(flask_login.current_user.timezone))
            return local_datetime.strftime(format)
    except ValueError:
        return utc_datetime


@jinja_filter('babel_format_date')
def custom_format_date(date, format='%Y-%m-%d'):
    if isinstance(date, datetime):
        datetime_obj = date
    else:
        datetime_obj = datetime.strptime(date, format)
    return format_date(datetime_obj)


@jinja_filter('babel_format_number')
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


@jinja_filter('format_quantity')
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


@jinja_filter()
def parse_datetime_string(datetime_string):
    return datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S')


@jinja_filter()
def default_format_datetime(utc_datetime: typing.Union[str, datetime]) -> str:
    return custom_format_datetime(utc_datetime, format='%Y-%m-%d %H:%M:%S')


@jinja_filter()
def convert_datetime_input(datetime_input):
    if not datetime_input:
        return ''
    try:
        local_datetime = datetime.strptime(datetime_input, flask_login.current_user.language.datetime_format_datetime)
        return local_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return ''


@jinja_filter()
def base64encode(value):
    return base64.b64encode(json.dumps(value).encode('utf8')).decode('ascii')


@jinja_filter('are_conditions_fulfilled')
def filter_are_conditions_fulfilled(data, property_schema) -> bool:
    if not data:
        return False
    if not isinstance(property_schema, dict):
        return False
    return are_conditions_fulfilled(property_schema.get('conditions'), data)


@jinja_filter()
def to_string_if_dict(data) -> str:
    if isinstance(data, dict):
        return str(data)
    else:
        return data


@jinja_filter()
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


@jinja_filter()
def to_datatype(obj):
    return json.loads(json.dumps(obj), object_hook=JSONEncoder.object_hook)


def get_style_aliases(style):
    return {
        'horizontal_table': ['table', 'horizontal_table'],
        'full_width_table': ['table']
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


@jinja_function()
def get_form_template(schema):
    return get_template('objects/forms/', 'form_', schema)


@jinja_function()
def get_view_template(schema):
    return get_template('objects/view/', '', schema)


@jinja_function()
def get_inline_edit_template(schema):
    return get_template('objects/inline_edit/', 'inline_edit_', schema)


@jinja_function()
def get_local_month_names():
    return [
        flask_babel.get_locale().months['format']['wide'][i]
        for i in range(1, 13)
    ]


@jinja_function()
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


@jinja_function()
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


@jinja_function()
def fingerprinted_static(filename: str) -> str:
    return flask.url_for(
        'static',
        filename=filename,
        v=get_fingerprint(os.path.join(STATIC_DIRECTORY, filename))
    )


@jinja_function()
def get_component_information_by_uuid(component_uuid: str):
    if component_uuid is None or component_uuid == flask.current_app.config['FEDERATION_UUID']:
        return None, 0, None
    else:
        try:
            component = get_component_by_uuid(component_uuid)
            return component.get_name(), component.id, component.address
        except errors.ComponentDoesNotExistError:
            return flask_babel.gettext('Unknown database (%(uuid)s)', uuid=component_uuid[:8]), -1, None


@jinja_function()
def get_component_information(component_id: int):
    try:
        component = get_component(component_id)
        component_name = component.name
        component_id = component.id
    except errors.ComponentDoesNotExistError:
        component_name = None
        component_id = -1
    return component_name, component_id


def get_search_paths(
        actions,
        action_types,
        path_depth_limit: typing.Optional[int] = None,
        valid_property_types: typing.Sequence[str] = (
            'text',
            'bool',
            'quantity',
            'datetime',
            'user',
            'object_reference',
            'sample',
            'measurement',
        )
):
    search_paths = {}
    search_paths_by_action = {}
    search_paths_by_action_type = {}
    for action_type in action_types:
        search_paths_by_action_type[action_type.id] = {}
    for action in actions:
        search_paths_by_action[action.id] = {}
        if action.type_id not in search_paths_by_action_type:
            search_paths_by_action_type[action.type_id] = {}
        for property_path, property_info in get_property_paths_for_schema(
                schema=action.schema,
                valid_property_types=set(valid_property_types),
                path_depth_limit=path_depth_limit
        ).items():
            property_path = '.'.join(
                key if key is not None else '?'
                for key in property_path
            )
            property_type = property_info.get('type')
            property_title = flask.escape(get_translated_text(property_info.get('title')))
            if property_type in {'object_reference', 'sample', 'measurement'}:
                # unify object_reference, sample and measurement
                property_type = 'object_reference'
            property_infos = {
                'types': [property_type],
                'titles': [property_title]
            }
            search_paths_by_action[action.id][property_path] = property_infos
            if property_path not in search_paths_by_action_type[action.type_id]:
                search_paths_by_action_type[action.type_id][property_path] = property_infos
            else:
                if property_title not in search_paths_by_action_type[action.type_id][property_path]['titles']:
                    search_paths_by_action_type[action.type_id][property_path]['titles'].append(property_title)
                if property_type not in search_paths_by_action_type[action.type_id][property_path]['types']:
                    search_paths_by_action_type[action.type_id][property_path]['types'].append(property_type)
            if property_path not in search_paths:
                search_paths[property_path] = property_infos
            else:
                if property_title not in search_paths[property_path]['titles']:
                    search_paths[property_path]['titles'].append(property_title)
                if property_type not in search_paths[property_path]['types']:
                    search_paths[property_path]['types'].append(property_type)
    return search_paths, search_paths_by_action, search_paths_by_action_type


@jinja_function()
def get_num_deprecation_warnings():
    return sum([
        show_admin_local_storage_warning(),
        show_load_objects_in_background_warning(),
    ])


@jinja_function()
def get_search_query(attribute, data, metadata_language=None):
    if data is None:
        return f'{attribute} == null'
    if data['_type'] == 'bool':
        if data['value']:
            return f'{attribute} == True'
        else:
            return f'{attribute} == False'
    if data['_type'] == 'datetime':
        return f'{attribute} == {data["utc_datetime"].split()[0]}'
    if data['_type'] == 'user':
        return f'{attribute} == #{data["user_id"]}'
    if data['_type'] in ('object_reference', 'sample', 'measurement'):
        return f'{attribute} == #{data["object_id"]}'
    if data['_type'] == 'quantity':
        if data['units'] == '1':
            return f'{attribute} == {data["magnitude_in_base_units"]}'
        else:
            return f'{attribute} == {to_datatype(data).magnitude}{data["units"]}'
    if data['_type'] == 'text':
        if data['text']:
            return f'{attribute} == "{get_translated_text(data["text"], metadata_language)}"'
        else:
            return f'{attribute} == ""'
    # fallback: find all objects that have this attribute set
    return f'!({attribute} == null)'
