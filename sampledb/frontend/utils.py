# coding: utf-8
"""

"""
import copy
import csv
import dataclasses
import decimal
import difflib
import io
import json
import base64
import functools
import hashlib
import os
import re
import typing
from io import BytesIO
from itertools import zip_longest
from urllib.parse import quote_plus
from datetime import datetime, timezone
from math import log10, floor

import flask
import flask_babel
import jinja2.filters
import werkzeug
from flask_babel import format_datetime, format_date, get_locale
from flask_login import current_user
from babel import numbers
import markupsafe
import qrcode
import qrcode.image.svg
import plotly
import pytz
import numpy as np

from ..logic import errors
from ..logic.caching import cache_per_request
from ..logic.components import get_component_or_none, get_component_id_by_uuid, get_component_by_uuid, Component
from ..logic.datatypes import Quantity
from ..logic.eln_import import get_eln_import_for_object, get_import_signed_by
from ..logic.errors import UserIsReadonlyError
from ..logic.units import prettify_units
from ..logic.notifications import get_num_notifications
from ..logic.markdown_to_html import markdown_to_safe_html
from ..logic.users import get_user, User, get_user_by_federated_user
from ..logic.utils import get_translated_text, get_all_translated_texts, show_numeric_tags_warning, relative_url_for
from ..logic.schemas.conditions import are_conditions_fulfilled
from ..logic.schemas.data_diffs import DataDiff, apply_diff, invert_diff
from ..logic.schemas.utils import get_property_paths_for_schema
from ..logic.schemas import get_default_data
from ..logic.actions import Action
from ..logic.action_types import ActionType
from ..logic.info_pages import InfoPage, get_info_pages_for_endpoint
from ..logic.instruments import Instrument
from ..logic.instrument_log_entries import InstrumentLogFileAttachment
from ..logic.action_permissions import get_sorted_actions_for_user, get_actions_with_permissions
from ..logic.languages import get_user_language
from ..logic.locations import Location, LocationType, get_location, get_unhandled_object_responsibility_assignments, is_full_location_tree_hidden, get_locations_tree
from ..logic.location_permissions import get_user_location_permissions, get_locations_with_user_permissions
from ..logic.datatypes import JSONEncoder
from ..logic.security_tokens import generate_token
from ..logic.object_permissions import get_user_object_permissions
from ..logic.objects import get_object
from ..logic.groups import Group, get_groups
from ..logic.projects import Project, get_projects, get_child_project_ids, get_parent_project_ids, get_project
from ..logic.group_categories import get_group_category_tree, get_group_categories, get_basic_group_categories, get_project_group_categories, get_full_group_category_name, GroupCategoryTree
from ..logic.files import File, get_file as get_file_logic
from ..models import Permissions, Object
from ..utils import generate_content_security_policy_nonce
from .info_pages import InfoPageAcknowledgementForm


class JinjaFilter:
    JinjaFilterT = typing.TypeVar('JinjaFilterT')
    filters: typing.Dict[str, typing.Any] = {}

    def __init__(self, name: str = '') -> None:
        self._name = name

    def __call__(self, func: JinjaFilterT) -> JinjaFilterT:
        if not self._name:
            self._name = func.__name__  # type: ignore[attr-defined]
        self.filters[self._name] = func
        return func


class JinjaFunction:
    JinjaFunctionT = typing.TypeVar('JinjaFunctionT')
    functions: typing.Dict[str, typing.Any] = {}

    def __init__(self, name: str = '') -> None:
        self._name = name

    def __call__(self, func: JinjaFunctionT) -> JinjaFunctionT:
        if not self._name:
            self._name = func.__name__  # type: ignore[attr-defined]
        self.functions[self._name] = func
        return func


JinjaFilter()(hash)
JinjaFilter()(prettify_units)
JinjaFilter('urlencode')(quote_plus)
JinjaFilter()(markdown_to_safe_html)
JinjaFilter()(get_translated_text)
JinjaFilter()(get_all_translated_texts)
JinjaFilter()(bool)

JinjaFunction()(get_component_or_none)
JinjaFunction()(get_component_id_by_uuid)
JinjaFunction()(get_unhandled_object_responsibility_assignments)
JinjaFunction()(is_full_location_tree_hidden)
JinjaFunction()(get_eln_import_for_object)
JinjaFunction()(relative_url_for)
JinjaFunction()(zip_longest)
JinjaFunction()(get_default_data)
JinjaFunction()(apply_diff)
JinjaFunction()(invert_diff)
JinjaFunction()(get_import_signed_by)
JinjaFunction()(InfoPageAcknowledgementForm)

qrcode_cache: typing.Dict[str, str] = {}


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


@JinjaFunction()
def get_file(
        file_id: int,
        object_id: int,
        component_uuid: typing.Optional[str] = None
) -> typing.Optional[File]:
    component_id = get_component_id_by_uuid(component_uuid)
    try:
        return get_file_logic(file_id, object_id, component_id)
    except errors.FileDoesNotExistError:
        return None


@JinjaFilter()
def has_preview(file: File) -> bool:
    if file.storage not in {'database', 'federation'}:
        return False
    if file.preview_image_binary_data and file.preview_image_mime_type:
        return True
    file_name = file.original_file_name
    file_extension = os.path.splitext(file_name)[1]
    return file_extension.lower() in flask.current_app.config.get('MIME_TYPES', {})


@JinjaFilter()
def has_preview_image(file: File) -> bool:
    if not file.preview_image_mime_type or not file.preview_image_binary_data:
        return is_image(file)
    mime_types: typing.Dict[str, str] = flask.current_app.config.get('MIME_TYPES', {})
    mime_type = file.preview_image_mime_type.lower()
    return mime_type in mime_types.values() and mime_type.startswith('image/')


def file_name_is_image(file_name: str) -> bool:
    file_extension = os.path.splitext(file_name)[1]
    mime_types: typing.Dict[str, str] = flask.current_app.config.get('MIME_TYPES', {})
    return mime_types.get(file_extension.lower(), '').startswith('image/')


@JinjaFilter()
def is_image(file: File) -> bool:
    # federation files are not recognized as images to prevent loading their thumbnails from other database
    if file.storage != 'database':
        return False
    return file_name_is_image(file.original_file_name)


@JinjaFilter()
def attachment_is_image(file_attachment: InstrumentLogFileAttachment) -> bool:
    return file_name_is_image(file_attachment.file_name)


@JinjaFilter()
def get_num_unread_notifications(user: User) -> int:
    return get_num_notifications(user.id, unread_only=True)


def check_current_user_is_not_readonly() -> None:
    if current_user.is_readonly:
        raise UserIsReadonlyError()


@JinjaFilter('plot')
def plotly_base64_image_from_json(object: typing.Dict[str, typing.Any]) -> typing.Optional[str]:
    try:
        fig_plot = plotly.io.from_json(json.dumps(object))
    except ValueError:
        return None
    image_stream = BytesIO()
    fig_plot.write_image(image_stream, "svg")
    image_stream.seek(0)
    return 'data:image/svg+xml;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')


@JinjaFilter()
def plotly_chart_get_title(plotly_object: typing.Dict[str, typing.Any]) -> str:
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


@JinjaFilter()
def to_json_no_extra_escapes(
        json_object: typing.Dict[str, typing.Any],
        indent: typing.Optional[int] = None
) -> str:
    return json.dumps(json_object, indent=indent)


@JinjaFilter('generic_format_datetime')
def generic_format_datetime(
        utc_datetime: typing.Union[str, datetime]
) -> str:
    """
    Returns a datetime in the common format and in UTC.

    :param utc_datetime: a datetime str or object in UTC
    :return: the formatted datetime
    """
    if isinstance(utc_datetime, str):
        # assume the datetime is already formatted
        return utc_datetime
    return utc_datetime.strftime('%Y-%m-%d %H:%M:%S')


@JinjaFilter('babel_format_datetime')
def custom_format_datetime(
        utc_datetime: typing.Union[str, datetime],
        format: typing.Optional[str] = None
) -> typing.Union[str, datetime]:
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
            if utc_datetime.tzinfo is None:
                utc_datetime = pytz.utc.localize(utc_datetime)
            local_datetime = utc_datetime.astimezone(pytz.timezone(current_user.timezone or 'UTC'))
            return local_datetime.strftime(format)
    except ValueError:
        return utc_datetime


@JinjaFilter('babel_format_date')
def custom_format_date(
        utc_datetime: typing.Union[datetime, str],
        format: typing.Optional[str] = None
) -> str:
    """
    Return a formatted date.

    :param utc_datetime: a datetime string or object in UTC
    :param format: the babel date format, or None
    :return: the formatted date
    """
    if isinstance(utc_datetime, str):
        utc_datetime = datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S')
    return format_date(utc_datetime, format=format)


@JinjaFilter('babel_format_time')
def custom_format_time(
        utc_datetime: typing.Union[str, datetime],
        format: typing.Optional[str] = None
) -> typing.Union[str, datetime]:
    """
    Return a formatted time.

    :param utc_datetime: a datetime string or object in UTC
    :param format: the babel time format, or None
    :return: the formatted time or utc_datetime in case of an error
    """
    try:
        if not isinstance(utc_datetime, datetime):
            utc_datetime = parse_datetime_string(utc_datetime)
        return flask_babel.format_time(utc_datetime, format=format)
    except ValueError:
        return utc_datetime


@JinjaFilter('format_int')
def format_int(decimal: int) -> str:
    locale = get_locale()
    return typing.cast(str, numbers.format_decimal(decimal, locale=locale))


@JinjaFilter('babel_format_number')
def custom_format_number(
    number: typing.Union[str, int, float, decimal.Decimal],
    display_digits: typing.Optional[int] = None,
    integral_digits: typing.Optional[int] = None,
    disable_scientific_format: bool = False
) -> str:
    """
    Return the formatted number.

    :param number: either an int or a float, or a string representation of either
    :param display_digits: number of decimals to use, or None
    :param integral_digits: minimal number of digits in the integral part, or None
    :param disable_scientific_format: disables output in scientific format
    :return: the formatted number
    """
    try:
        # if number is a string that can not be formatted. Wrong inputs...
        number = float(number)
    except ValueError:
        return typing.cast(str, number)
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
    if not disable_scientific_format:
        # for very small or very large absolute numbers, the exponential format should be used
        use_exponential_format = not -5 < exponent < 6
    else:
        exponent = 0
        use_exponential_format = False

    if integral_digits is not None:
        positive_format = '0' * integral_digits
    else:
        positive_format = '0'
    if display_digits is not None:
        if use_exponential_format:
            display_digits += exponent
            if display_digits > 15:
                display_digits = 15
        else:
            internal_integral_digits = max(0, exponent + 1)
            if display_digits + internal_integral_digits > 15:
                display_digits = 15 - internal_integral_digits
            if display_digits < 0:
                display_digits = 0

        positive_format = positive_format + '.' + '0' * display_digits
    else:
        positive_format = positive_format + '.###'
    if use_exponential_format:
        # including E will enable exponential format, 0 means the exponent should be shown even if 0
        positive_format += 'E0'
    negative_format = '-' + positive_format
    f = positive_format + ';' + negative_format

    if use_exponential_format:
        return numbers.format_scientific(
            number,
            locale=locale,
            format=f,
            decimal_quantization=False
        )
    else:
        # babel.numbers doesn't explicitly export decimal, but it is
        # recommended to use babel.numbers.decimal instead of the standard
        # library module, in case babel decides to use a different decimal
        # implementation in the future
        with numbers.decimal.localcontext() as ctx:  # type: ignore[attr-defined]
            ctx.prec = 15
            return typing.cast(str, numbers.format_decimal(
                numbers.decimal.Decimal(number),  # type: ignore[attr-defined]
                locale=locale,
                format=f,
                decimal_quantization=False
            ))


@JinjaFilter('format_time')
def format_time(
    magnitude_in_base_units: float,
    units: str,
    display_digits: typing.Optional[int] = None
) -> str:
    if units not in {'min', 'h'}:
        raise errors.MismatchedUnitError()
    decimal = 0.0
    magnitude_str = str(magnitude_in_base_units)
    if '.' in magnitude_str:
        # string manipulation to prevent ugly float-arithmetics
        integral_str, decimal_str = magnitude_str.split('.', maxsplit=1)
        magnitude_in_base_units = int(integral_str)
        decimal = float(f'0.{decimal_str}')
    seconds = magnitude_in_base_units % 60
    magnitude_in_base_units -= seconds
    seconds += decimal
    if units == 'h':
        minutes = int(magnitude_in_base_units // 60) % 60
        magnitude_in_base_units -= minutes * 60
        hours = int(magnitude_in_base_units // 3600)
        return f'{hours:02d}:{minutes:02d}:{custom_format_number(seconds, display_digits, 2, True)}'
    if units == 'min':
        minutes = int(magnitude_in_base_units // 60)
        return f'{minutes:02d}:{custom_format_number(seconds, display_digits, 2, True)}'
    # fall back to regular quantity formatting
    return custom_format_quantity(
        data={
            'magnitude_in_base_units': magnitude_in_base_units,
            'units': units
        },
        schema={
            'display_digits': display_digits
        }
    )


@JinjaFilter('format_quantity')
def custom_format_quantity(
        data: typing.Optional[typing.Dict[str, typing.Any]],
        schema: typing.Dict[str, typing.Any]
) -> str:
    if data is None:
        mdash = '\u2014'
        return mdash
    if data.get('units', '1') in {'1', ''}:
        return custom_format_number(data.get('magnitude_in_base_units', 0), schema.get('display_digits', None))
    narrow_non_breaking_space = '\u202f'
    magnitude = data.get('magnitude_in_base_units', 0)
    units = data.get('units')
    if units in {'h', 'min'}:
        return f'{format_time(magnitude, units, schema.get("display_digits"))}{narrow_non_breaking_space}{data.get("units")}'
    quantity = Quantity.from_json(data)
    return custom_format_number(quantity.magnitude, schema.get('display_digits', None)) + narrow_non_breaking_space + prettify_units(quantity.units)


@JinjaFilter()
def parse_datetime_string(datetime_string: str) -> datetime:
    return datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)


@JinjaFilter()
def default_format_datetime(utc_datetime: typing.Union[str, datetime]) -> typing.Union[str, datetime]:
    return custom_format_datetime(utc_datetime, format='%Y-%m-%d %H:%M:%S')


@JinjaFilter()
def convert_datetime_input(datetime_input: str) -> str:
    if not datetime_input:
        return ''
    try:
        user_language = get_user_language(current_user)
        local_datetime = datetime.strptime(datetime_input, user_language.datetime_format_datetime)
        return local_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return ''


@JinjaFilter()
def base64encode(value: typing.Any) -> str:
    return base64.b64encode(json.dumps(value, separators=(',', ':')).encode('utf8')).decode('ascii')


@JinjaFilter('are_conditions_fulfilled')
def filter_are_conditions_fulfilled(data: typing.Dict[str, typing.Any], property_schema: typing.Dict[str, typing.Any]) -> bool:
    if not isinstance(property_schema, dict):
        return False
    if not data and 'conditions' in property_schema:
        return False
    return are_conditions_fulfilled(property_schema.get('conditions'), data)


@typing.overload
def to_string_if_dict(data: typing.Dict[str, typing.Any]) -> str:
    ...


@typing.overload
def to_string_if_dict(data: typing.Any) -> typing.Any:
    ...


@JinjaFilter()
def to_string_if_dict(data: typing.Any) -> typing.Any:
    if isinstance(data, dict):
        return str(data)
    else:
        return data


@JinjaFilter()
def get_location_name(
        location_or_location_id: typing.Union[int, Location],
        include_id: bool = False,
        language_code: typing.Optional[str] = None,
        has_read_permissions: typing.Optional[bool] = None
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

    if location is not None and has_read_permissions is None:
        has_read_permissions = Permissions.READ in get_user_location_permissions(location_id, current_user.id)

    if location is None or not has_read_permissions:
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


@JinjaFilter()
def get_full_location_name(
        location_or_location_id: typing.Union[int, Location],
        include_id: bool = False,
        language_code: typing.Optional[str] = None
) -> str:
    location: typing.Optional[Location]
    if type(location_or_location_id) is int:
        location_id: int = location_or_location_id
        try:
            location = get_location(location_id)
        except errors.LocationDoesNotExistError:
            location = None
    elif isinstance(location_or_location_id, Location):
        location = location_or_location_id
    else:
        location = None
    if location is None:
        return flask_babel.gettext("Unknown Location")

    full_location_name = get_location_name(location, include_id=include_id, language_code=language_code)
    while location.parent_location_id is not None:
        location = get_location(location.parent_location_id)
        full_location_name = get_location_name(location, include_id=False, language_code=language_code) + ' / ' + full_location_name
    return full_location_name


@JinjaFilter()
def to_datatype(obj: typing.Any) -> typing.Any:
    return json.loads(json.dumps(obj), object_hook=JSONEncoder.object_hook)


def get_style_aliases(style: str) -> typing.List[str]:
    return {
        'choice': ['list', 'choice'],
        'horizontal_table': ['table', 'horizontal_table'],
        'full_width_table': ['table']
    }.get(style, [style])


@JinjaFunction()
def get_style_variant(
        style: typing.Optional[typing.Union[str, typing.Dict[str, str]]],
        template_mode: str
) -> typing.Optional[str]:
    if isinstance(style, str):
        return style
    if isinstance(style, dict):
        if template_mode not in style and template_mode == 'inline_edit':
            template_mode = 'view'
        return style.get(template_mode)
    return None


def get_template(template_mode: str, default_prefix: str, schema: typing.Dict[str, typing.Any], container_style: typing.Optional[str]) -> str:
    return get_template_impl(
        template_mode=template_mode,
        default_prefix=default_prefix,
        schema_type=schema['type'],
        schema_style=get_style_variant(schema.get('style'), template_mode),
        container_style=get_style_variant(container_style, template_mode)
    )


@functools.cache
def get_template_impl(template_mode: str, default_prefix: str, schema_type: str, schema_style: typing.Optional[str], container_style: typing.Optional[str]) -> str:
    template_folder = {
        'view': 'objects/view/',
        'inline_edit': 'objects/inline_edit/',
        'form': 'objects/forms/'
    }.get(template_mode, 'objects/view/')
    system_path = os.path.join(os.path.dirname(__file__), 'templates', template_folder)
    base_file = str(schema_type) + ".html"

    file_order = [default_prefix + base_file]
    if container_style:
        for container_style_alias in get_style_aliases(container_style):
            file_order.insert(0, (default_prefix + container_style_alias + "_" + base_file))
    if schema_style:
        for style in get_style_aliases(schema_style):
            file_order.insert(0, (default_prefix + style + "_" + base_file))
    if container_style and schema_style:
        for style in get_style_aliases(schema_style):
            for container_style_alias in get_style_aliases(container_style):
                file_order.insert(0, (default_prefix + container_style_alias + "_" + style + "_" + base_file))

    for file in file_order:
        if os.path.exists(os.path.join(system_path, file)):
            return template_folder + file

    return template_folder + default_prefix + base_file


def get_property_template(template_mode: str, schema: typing.Dict[str, typing.Any], container_style: typing.Optional[typing.Union[str, typing.Dict[str, str]]]) -> str:
    return get_property_template_impl(
        template_mode=template_mode,
        schema_style=get_style_variant(schema.get('style'), template_mode),
        container_style=get_style_variant(container_style, template_mode)
    )


@functools.cache
def get_property_template_impl(template_mode: str, schema_style: typing.Optional[str], container_style: typing.Optional[str]) -> str:
    template_folder = {
        'view': 'objects/view/',
        'inline_edit': 'objects/inline_edit/',
        'form': 'objects/forms/'
    }.get(template_mode, 'objects/view/')
    system_path = os.path.join(os.path.dirname(__file__), 'templates', template_folder)

    file_order = ['regular_property.html']
    if container_style:
        for container_style_alias in get_style_aliases(container_style):
            file_order.insert(0, container_style_alias + '_property.html')
    if schema_style:
        for style in get_style_aliases(schema_style):
            file_order.insert(0, style + '_property.html')

    for file in file_order:
        if os.path.exists(os.path.join(system_path, file)):
            return os.path.join(template_folder, file)

    return os.path.join(template_folder + 'regular_property.html')


@JinjaFunction()
def get_form_property_template(schema: typing.Dict[str, typing.Any], container_style: typing.Optional[str]) -> str:
    return get_property_template('form', schema, container_style)


@JinjaFunction()
def get_view_property_template(schema: typing.Dict[str, typing.Any], container_style: typing.Optional[str]) -> str:
    return get_property_template('view', schema, container_style)


@JinjaFunction()
def get_inline_edit_property_template(schema: typing.Dict[str, typing.Any], container_style: typing.Optional[str]) -> str:
    return get_property_template('inline_edit', schema, container_style)


@JinjaFunction()
def get_form_template(schema: typing.Dict[str, typing.Any], container_style: typing.Optional[str]) -> str:
    return get_template('form', 'form_', schema, container_style)


@JinjaFunction()
def get_view_template(schema: typing.Dict[str, typing.Any], container_style: typing.Optional[str]) -> str:
    return get_template('view', '', schema, container_style)


@JinjaFunction()
def get_inline_edit_template(schema: typing.Dict[str, typing.Any], container_style: typing.Optional[str]) -> str:
    return get_template('inline_edit', 'inline_edit_', schema, container_style)


@JinjaFunction()
def get_local_month_names() -> typing.List[str]:
    locale = flask_babel.get_locale()
    if locale is None:
        return [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December"
        ]
    else:
        return [
            locale.months['format']['wide'][i]
            for i in range(1, 13)
        ]


@JinjaFunction()
def get_templates(user_id: int) -> typing.List[Action]:
    return [
        action
        for action in get_sorted_actions_for_user(user_id=user_id)
        if action.type is not None and action.type.is_template and action.schema
    ]


@JinjaFunction()
def get_local_decimal_delimiter() -> str:
    return typing.cast(str, numbers.format_decimal(1.2346, locale=flask_babel.get_locale())[1:2])


@JinjaFunction()
def get_user_if_exists(user_id: int, component_id: typing.Optional[int] = None) -> typing.Optional[User]:
    try:
        return get_user(user_id, component_id)
    except errors.UserDoesNotExistError:
        return None
    except errors.ComponentDoesNotExistError:
        return None


@functools.lru_cache(maxsize=None)
def _get_fingerprint(file_path: str) -> str:
    """
    Calculate a fingerprint for a given file.

    :param file_path: path to the file that should be fingerprinted
    :return: the file fingerprint, or an empty string
    """
    try:
        block_size = 65536
        hash_method = hashlib.sha256()
        with open(file_path, 'rb') as input_file:
            buf = input_file.read(block_size)
            while buf:
                hash_method.update(buf)
                buf = input_file.read(block_size)
        return 'sha256-' + base64.b64encode(hash_method.digest()).decode('utf-8')
    except Exception:
        # if the file cannot be hashed for any reason, return an empty fingerprint
        return ''


STATIC_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))


@JinjaFunction()
def fingerprinted_static(filename: str) -> str:
    fingerprint = _get_fingerprint(os.path.join(STATIC_DIRECTORY, filename))
    url = flask.url_for(
        'static',
        filename=filename,
        v=fingerprint or None
    )
    file_extension = os.path.splitext(filename)[1]
    result = markupsafe.escape(url)
    # add integrity attribute for script files and stylesheets for SRI
    if file_extension in ('.js', '.css') and fingerprint and not flask.current_app.config['DEBUG']:
        result = result + markupsafe.Markup('" integrity="' + fingerprint)
    # add a nonce for script files for CSP
    if file_extension == '.js':
        nonce = generate_content_security_policy_nonce()
        result = result + markupsafe.Markup('" nonce="' + nonce)
    return result


class SearchPathInfo(typing.TypedDict):
    types: typing.List[str]
    titles: typing.List[str]


def get_search_paths(
        actions: typing.List[Action],
        action_types: typing.List[ActionType],
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
            'tags',
        ),
        include_file_name: bool = False
) -> typing.Tuple[typing.Dict[str, SearchPathInfo], typing.Dict[typing.Optional[int], typing.Dict[str, SearchPathInfo]], typing.Dict[typing.Optional[int], typing.Dict[str, SearchPathInfo]]]:
    search_paths: typing.Dict[str, SearchPathInfo] = {}
    search_paths_by_action: typing.Dict[typing.Optional[int], typing.Dict[str, SearchPathInfo]] = {}
    search_paths_by_action_type: typing.Dict[typing.Optional[int], typing.Dict[str, SearchPathInfo]] = {}
    for action_type in action_types:
        search_paths_by_action_type[action_type.id] = {}
    for action in actions:
        if not action.schema:
            continue
        search_paths_by_action[action.id] = {}
        if action.type_id not in search_paths_by_action_type:
            search_paths_by_action_type[action.type_id] = {}
        property_infos = []
        for property_path, property_info in get_property_paths_for_schema(
                schema=action.schema,
                valid_property_types=set(valid_property_types),
                path_depth_limit=path_depth_limit
        ).items():
            property_path = '.'.join(
                key if key is not None else '?'
                for key in property_path
            )
            property_type = str(property_info.get('type', ''))
            property_title = markupsafe.escape(get_translated_text(property_info.get('title')))
            if property_type in {'object_reference', 'sample', 'measurement'}:
                # unify object_reference, sample and measurement
                property_type = 'object_reference'
            property_infos.append((property_path, property_type, property_title))
        if include_file_name and action.type and action.type.enable_files and 'text' in valid_property_types:
            property_infos.append(('file_name', 'text', markupsafe.escape('File Name')))
        for property_path, property_type, property_title in property_infos:
            search_paths_by_action[action.id][property_path] = SearchPathInfo(
                types=[property_type],
                titles=[property_title]
            )
            if property_path not in search_paths_by_action_type[action.type_id]:
                search_paths_by_action_type[action.type_id][property_path] = SearchPathInfo(
                    types=[property_type],
                    titles=[property_title]
                )
            else:
                if property_title not in search_paths_by_action_type[action.type_id][property_path]['titles']:
                    search_paths_by_action_type[action.type_id][property_path]['titles'].append(property_title)
                if property_type not in search_paths_by_action_type[action.type_id][property_path]['types']:
                    search_paths_by_action_type[action.type_id][property_path]['types'].append(property_type)
            if property_path not in search_paths:
                search_paths[property_path] = SearchPathInfo(
                    types=[property_type],
                    titles=[property_title]
                )
            else:
                if property_title not in search_paths[property_path]['titles']:
                    search_paths[property_path]['titles'].append(property_title)
                if property_type not in search_paths[property_path]['types']:
                    search_paths[property_path]['types'].append(property_type)
    return search_paths, search_paths_by_action, search_paths_by_action_type


@JinjaFunction()
def get_num_deprecation_warnings() -> int:
    return sum([
        show_numeric_tags_warning(),
    ])


@JinjaFunction()
def get_search_url(
        property_path: typing.Tuple[str, ...],
        data: typing.Optional[typing.Union[typing.List[typing.Any], typing.Dict[str, typing.Any]]],
        metadata_language: typing.Optional[str] = None
) -> typing.Optional[str]:
    search_query = get_search_query(property_path, data, metadata_language=metadata_language)
    if search_query is None:
        return None
    return flask.url_for(
        '.objects',
        q=search_query,
        advanced='on'
    )


def get_search_query(
        property_path: typing.Tuple[str, ...],
        data: typing.Optional[typing.Union[typing.List[typing.Any], typing.Dict[str, typing.Any]]],
        metadata_language: typing.Optional[str] = None
) -> typing.Optional[str]:
    attribute = '.'.join(
        str(path_element)
        for path_element in property_path
    )
    if data is None:
        return f'{attribute} == null'
    if isinstance(data, list):
        return None
    if data['_type'] in ('object', 'hazards'):
        return None
    if data['_type'] == 'bool':
        if data['value']:
            return f'{attribute} == True'
        else:
            return f'{attribute} == False'
    if data['_type'] == 'datetime':
        utc_datetime = datetime.strptime(data["utc_datetime"], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        local_timezone = pytz.timezone(current_user.timezone if hasattr(current_user, 'timezone') and current_user.timezone is not None else 'UTC')
        local_datetime = utc_datetime.astimezone(local_timezone)
        local_date = local_datetime.date()
        return f'{attribute} == {local_date.year}-{local_date.month:02d}-{local_date.day:02d}'
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
    if data['_type'] == 'tags':
        return '#' + ' and #'.join(data['tags'])
    if data['_type'] == 'plotly_chart':
        title = jinja2.filters.do_striptags(plotly_chart_get_title(data['plotly']))
        if title:
            return f'{attribute} == "{str(title)}"'
        else:
            return f'{attribute} == ""'
    # fallback: find all objects that have this attribute set
    return f'!({attribute} == null)'


@JinjaFunction()
def get_table_search_url(
        property_path: typing.Tuple[str, ...],
        schema: typing.Dict[str, typing.Any]
) -> typing.Optional[str]:
    search_query = get_table_search_query(property_path, schema)
    if search_query is None:
        return None
    return flask.url_for(
        '.objects',
        q=search_query,
        advanced='on'
    )


def get_table_search_query(
        property_path: typing.Tuple[str, ...],
        schema: typing.Dict[str, typing.Any]
) -> typing.Optional[str]:
    attribute = '.'.join(
        str(path_element)
        for path_element in property_path
    )
    if schema.get('type') == 'text':
        return f'{attribute} == ""'
    if schema.get('type') == 'quantity':
        if isinstance(schema['units'], str) and schema['units'].strip() != '1':
            return f'{attribute} == 0{schema.get("units")}'
        if isinstance(schema['units'], list) and len(schema['units']) == 1 and schema['units'][0].strip() != '1':
            return f'{attribute} == 0{schema.get("units")}'
        return f'{attribute} == 0'
    if schema.get('type') == 'bool':
        return f'{attribute} == True'
    # fallback: find all objects that have this attribute set
    return f'!({attribute} == null)'


@JinjaFunction()
def build_object_location_assignment_confirmation_url(object_location_assignment_id: int) -> str:
    confirmation_url = flask.url_for(
        'frontend.accept_responsibility_for_object',
        t=generate_token(
            object_location_assignment_id,
            salt='confirm_responsibility',
            secret_key=flask.current_app.config['SECRET_KEY']
        ),
        _external=True
    )
    return confirmation_url


@JinjaFunction()
def build_object_location_assignment_declination_url(object_location_assignment_id: int) -> str:
    confirmation_url = flask.url_for(
        'frontend.decline_responsibility_for_object',
        t=generate_token(
            object_location_assignment_id,
            salt='decline_responsibility',
            secret_key=flask.current_app.config['SECRET_KEY']
        ),
        _external=True
    )
    return confirmation_url


@JinjaFunction()
def get_object_name_if_user_has_permissions(object_id: int) -> str:
    fallback_name = f"{flask_babel.gettext('Object')} #{object_id}"
    try:
        permissions = get_user_object_permissions(object_id, current_user.id)
        if Permissions.READ in permissions:
            object = get_object(object_id)
            if object.data:
                object_name = get_translated_text(object.data['name']['text'])
                return f"{object_name} (#{object_id})"
    except errors.ObjectDoesNotExistError:
        pass
    return fallback_name


def validate_orcid(orcid: str) -> typing.Tuple[bool, typing.Optional[str]]:
    # accept full ORCID iDs
    orcid_prefix = 'https://orcid.org/'
    if orcid.startswith(orcid_prefix):
        orcid = orcid[len(orcid_prefix):]
    # check ORCID iD syntax
    if not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]', orcid, flags=re.ASCII):
        return False, None
    # check ISO 7064 Mod 11, 2 checksum
    checksum = '0123456789X'[(12 - sum(
        int(digit) << index
        for index, digit in enumerate(reversed(orcid.replace('-', '')[:-1]), start=1)
    ) % 11) % 11]
    if checksum != orcid[-1]:
        return False, None
    # return sanitized ORCID iD on success
    return True, orcid


@dataclasses.dataclass(frozen=True)
class FederationRef:
    fed_id: int
    component_uuid: str
    referenced_class: typing.Type[typing.Any]

    @dataclasses.dataclass(frozen=True)
    class FederationComponentMock:
        name: str
        address: typing.Optional[str]

        def get_name(self) -> str:
            return self.name

    @property
    def component(self) -> typing.Union[Component, FederationComponentMock]:
        try:
            return get_component_by_uuid(self.component_uuid)
        except errors.ComponentDoesNotExistError:
            return FederationRef.FederationComponentMock(
                name=flask_babel.gettext('Unknown database (%(uuid)s)', uuid=self.component_uuid[:8]),
                address=None
            )


@JinjaFunction()
@dataclasses.dataclass(frozen=True)
class FederationObjectRef(FederationRef):
    referenced_class: typing.Type[Object] = Object


@JinjaFunction()
@dataclasses.dataclass(frozen=True)
class FederationUserRef(FederationRef):
    referenced_class: typing.Type[User] = User


@JinjaFunction()
@dataclasses.dataclass(frozen=True)
class ELNImportObjectRef:
    eln_import_id: int
    eln_object_id: int


@JinjaFunction()
def wrap_object_ref(
        *,
        fed_id: typing.Optional[int] = None,
        component_uuid: typing.Optional[str] = None,
        eln_import_id: typing.Optional[int] = None,
        eln_object_id: typing.Optional[int] = None
) -> typing.Optional[typing.Union[FederationObjectRef, ELNImportObjectRef]]:
    if fed_id is not None and component_uuid is not None:
        return FederationObjectRef(
            fed_id=fed_id,
            component_uuid=component_uuid
        )
    if eln_import_id is not None and eln_object_id is not None:
        return ELNImportObjectRef(
            eln_import_id=eln_import_id,
            eln_object_id=eln_object_id
        )
    return None


@JinjaFunction()
def get_federation_url(obj: typing.Any) -> str:
    component_address: str = obj.component.address
    if not component_address.endswith('/'):
        component_address = component_address + '/'
    if isinstance(obj, FederationRef):
        obj_class = obj.referenced_class
    else:
        obj_class = obj.__class__
    endpoint_and_param_name = {
        User: ('frontend.user_profile', 'user_id'),
        Object: ('frontend.object', 'object_id'),
        Action: ('frontend.action', 'action_id'),
        ActionType: ('frontend.action_type', 'type_id'),
        Instrument: ('frontend.instrument', 'instrument_id'),
        Location: ('frontend.location', 'location_id'),
        LocationType: ('frontend.location_type', 'type_id'),
    }.get(obj_class)
    if endpoint_and_param_name is None:
        return component_address
    else:
        endpoint, param_name = endpoint_and_param_name
        return component_address + relative_url_for(endpoint, **{param_name: obj.fed_id})


@dataclasses.dataclass(frozen=True, kw_only=True)
class LocationFormInformation:
    id: int
    name: str
    name_prefix: str
    id_path: typing.Sequence[int]
    has_subtree: bool
    is_fed: bool
    is_disabled: bool

    @property
    def full_name(self) -> str:
        return self.name_prefix + self.name

    @property
    def id_string(self) -> str:
        return str(self.id)


def get_locations_form_data(
        filter: typing.Callable[[Location], bool]
) -> typing.Tuple[typing.Sequence[LocationFormInformation], typing.Sequence[typing.Tuple[str, str]]]:
    """
    Get location information for a location form field.

    :param filter: a filter for which locations should be valid
    :return: a list of location information and a list of valid choices
    """
    readable_location_ids = {
        location.id
        for location in get_locations_with_user_permissions(current_user.id, Permissions.READ)
    }
    locations_map, locations_tree = get_locations_tree()
    readable_locations_map = {
        location_id: location
        for location_id, location in locations_map.items()
        if location_id in readable_location_ids
    }
    all_choices = [LocationFormInformation(
        id=-1,
        name='—',
        name_prefix='',
        id_path=[],
        has_subtree=False,
        is_fed=False,
        is_disabled=False
    )]
    choices = [
        ('-1', '')
    ]
    unvisited_location_ids_prefixes_and_subtrees = [
        (location_id, '', location, [location_id])
        for location_id, location in locations_tree.items()
    ]
    while unvisited_location_ids_prefixes_and_subtrees:
        location_id, name_prefix, subtree, id_path = unvisited_location_ids_prefixes_and_subtrees.pop(0)
        location = locations_map[location_id]
        # skip hidden locations with a fully hidden subtree
        is_full_subtree_hidden = is_full_location_tree_hidden(readable_locations_map, subtree)
        if not current_user.is_admin and location.is_hidden and is_full_subtree_hidden:
            continue
        has_read_permissions = location_id in readable_location_ids
        # skip unreadable locations, but allow processing their child locations
        # in case any of them are readable
        if has_read_permissions and (not location.is_hidden or current_user.is_admin):
            is_disabled = not filter(location)
            all_choices.append(LocationFormInformation(
                id=location_id,
                name=get_location_name(location, include_id=True, has_read_permissions=has_read_permissions),
                name_prefix=name_prefix,
                id_path=tuple(id_path),
                has_subtree=bool(subtree),
                is_fed=location.fed_id is not None,
                is_disabled=is_disabled
            ))
            if not is_disabled:
                choices.append((str(all_choices[-1].id), all_choices[-1].full_name))
        elif not is_full_subtree_hidden:
            all_choices.append(LocationFormInformation(
                id=location_id,
                name=get_location_name(location, include_id=True, has_read_permissions=has_read_permissions),
                name_prefix=name_prefix,
                id_path=tuple(id_path),
                has_subtree=bool(subtree),
                is_fed=False,
                is_disabled=True,
            ))
        else:
            continue
        name_prefix = f'{name_prefix}{get_location_name(location, has_read_permissions=has_read_permissions)} / '
        for location_id in sorted(subtree, key=lambda location_id: get_location_name(locations_map[location_id], has_read_permissions=location_id in readable_location_ids), reverse=True):
            unvisited_location_ids_prefixes_and_subtrees.insert(0, (location_id, name_prefix, subtree[location_id], id_path + [location_id]))
    return all_choices, choices


@JinjaFunction()
def get_user_or_none(user_id: int, component_id: typing.Optional[int] = None) -> typing.Optional[User]:
    try:
        return get_user(user_id, component_id=component_id)
    except errors.UserDoesNotExistError:
        return None


@dataclasses.dataclass(frozen=True, kw_only=True)
class GroupFormInformation:
    id: int
    name: str
    name_prefix: str
    id_path: typing.Sequence[int]
    has_subtree: bool
    is_disabled: bool

    @property
    def full_name(self) -> str:
        return self.name_prefix + self.name


def get_groups_form_data(
        basic_group_filter: typing.Optional[typing.Callable[[Group], bool]] = None,
        project_group_filter: typing.Optional[typing.Callable[[Project], bool]] = None
) -> typing.Tuple[bool, typing.Sequence[GroupFormInformation]]:
    """
    Get group form information usable with a treepicker, e.g. for permission forms.

    :param basic_group_filter: filter for basic groups to include, or None to
        exclude all basic groups
    :param project_group_filter: filter for project groups to include, or None
        to exclude all project groups
    :return: a tuple containing whether any group is enabled and the group
        form information list
    """
    if basic_group_filter is not None:
        all_basic_groups = get_groups()
        basic_group_names_by_id = {
            group.id: get_translated_text(
                group.name,
                default=flask_babel.gettext('Basic Group') + ' #' + str(group.id)
            )
            for group in all_basic_groups
        }
        valid_basic_group_ids = {
            group.id
            for group in all_basic_groups
            if basic_group_filter(group)
        }
    if project_group_filter is not None:
        all_project_groups = get_projects()
        project_group_names_by_id = {
            group.id: get_translated_text(
                group.name,
                default=flask_babel.gettext('Project Group') + ' #' + str(group.id)
            )
            for group in all_project_groups
        }
        valid_project_group_ids = {
            group.id
            for group in all_project_groups
            if project_group_filter(group)
        }
        child_project_group_ids_by_id = {
            group.id: [
                child_group_id
                for child_group_id in get_child_project_ids(group.id)
                if child_group_id in valid_project_group_ids
            ]
            for group in all_project_groups
        }
    else:
        project_group_names_by_id = {}
        child_project_group_ids_by_id = {}
    all_group_categories = get_group_categories()
    group_category_names_by_id = {
        group_category.id: get_translated_text(
            group_category.name,
            default=flask_babel.gettext('Group Category') + ' #' + str(group_category.id)
        )
        for group_category in all_group_categories
    }
    group_category_tree = get_group_category_tree(
        basic_group_ids=None if basic_group_filter is not None else set(),
        project_group_ids=None if project_group_filter is not None else set()
    )
    all_choices = []

    def _add_project_group_to_all_choices(
            id_path: typing.List[int],
            name_prefix: str,
            group_id: int
    ) -> None:
        if not id_path and get_parent_project_ids(group_id):
            return
        child_project_ids = child_project_group_ids_by_id[group_id]
        project_group_name = project_group_names_by_id[group_id]
        all_choices.append(GroupFormInformation(
            id=group_id,
            name=project_group_name,
            name_prefix=name_prefix,
            id_path=id_path + [group_id],
            has_subtree=bool(child_project_ids),
            is_disabled=group_id not in valid_project_group_ids
        ))
        name_prefix = name_prefix + project_group_name + ' / '
        id_path = id_path + [group_id]
        for child_project_id in sorted(child_project_ids, key=lambda group_id: project_group_names_by_id[group_id]):
            _add_project_group_to_all_choices(
                id_path, name_prefix, child_project_id
            )

    def _fill_all_choices(
            id_path: typing.List[int],
            name_prefix: str,
            group_category_id: typing.Optional[int],
            group_category_tree: GroupCategoryTree
    ) -> None:
        if not group_category_tree['contains_basic_groups'] and not group_category_tree['contains_project_groups']:
            return
        if group_category_id is not None:
            group_category_name = group_category_names_by_id[group_category_id]
            all_choices.append(GroupFormInformation(
                id=-group_category_id,
                name=group_category_name,
                name_prefix=name_prefix,
                id_path=id_path + [-group_category_id],
                has_subtree=True,
                is_disabled=True
            ))
            name_prefix = name_prefix + group_category_name + ' / '
            id_path = id_path + [-group_category_id]
        for group_category_id, group_category_subtree in group_category_tree['child_categories'].items():
            _fill_all_choices(id_path, name_prefix, group_category_id, group_category_subtree)
        if basic_group_filter is not None:
            for group_id in sorted(group_category_tree['basic_group_ids'], key=lambda group_id: basic_group_names_by_id[group_id]):
                all_choices.append(GroupFormInformation(
                    id=group_id,
                    name=basic_group_names_by_id[group_id],
                    name_prefix=name_prefix,
                    id_path=id_path + [group_id],
                    has_subtree=False,
                    is_disabled=group_id not in valid_basic_group_ids
                ))
        if project_group_filter is not None:
            for group_id in sorted(group_category_tree['project_group_ids'], key=lambda group_id: project_group_names_by_id[group_id]):
                _add_project_group_to_all_choices(id_path, name_prefix, group_id)

    _fill_all_choices([], '', None, group_category_tree)

    # filter out subtrees only containing disabled options
    enabled_id_paths = {
        tuple(group_form_information.id_path)
        for group_form_information in all_choices
        if not group_form_information.is_disabled
    }
    all_choices = [
        group_form_information
        for group_form_information in all_choices
        if not group_form_information.is_disabled or (group_form_information.has_subtree and any(
            tuple(group_form_information.id_path) == id_path[:len(group_form_information.id_path)]
            for id_path in enabled_id_paths
        ))
    ]
    any_choice_enabled = any(
        not group_form_information.is_disabled
        for group_form_information in all_choices
    )

    return any_choice_enabled, all_choices


@JinjaFunction()
def get_basic_group_name_prefixes(group_id: int) -> typing.List[str]:
    group_categories = get_basic_group_categories(group_id)
    return sorted([
        ' / '.join(
            get_translated_text(category_name, default=flask_babel.gettext("Unnamed Category"))
            for category_name in get_full_group_category_name(group_category.id)
        ) + ' / '
        for group_category in group_categories
    ])


@JinjaFunction()
def get_project_group_name_prefixes(project_id: int) -> typing.List[str]:
    group_categories = get_project_group_categories(project_id)
    name_prefixes = [
        ' / '.join(
            get_translated_text(category_name, default=flask_babel.gettext("Unnamed Category"))
            for category_name in get_full_group_category_name(group_category.id)
        ) + ' / '
        for group_category in group_categories
    ]
    parent_project_ids = get_parent_project_ids(project_id)
    for parent_project_id in parent_project_ids:
        parent_project = get_project(parent_project_id)
        parent_project_name = get_translated_text(parent_project.name, default=flask_babel.gettext("Unnamed Project Group"))
        parent_project_name_prefixes = get_project_group_name_prefixes(parent_project_id)
        if parent_project_name_prefixes:
            for parent_project_name_prefix in parent_project_name_prefixes:
                name_prefixes.append(parent_project_name_prefix + parent_project_name + ' / ')
        else:
            name_prefixes.append(parent_project_name + ' / ')
    return sorted(name_prefixes)


@JinjaFilter()
def to_timeseries_data(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
    utc_datetimes: typing.List[datetime] = []
    relative_times: typing.List[typing.Union[int, float]] = []
    if isinstance(data['data'][0][0], str):
        entries = list(sorted(
            (datetime.strptime(entry[0], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc), entry[1], entry[2])
            for entry in data['data']
        ))
        utc_datetimes = [
            entry[0]
            for entry in entries
        ]
        magnitudes = [
            entry[1]
            for entry in entries
        ]
    else:
        r_entries = list(sorted((entry[0], entry[1], entry[2]) for entry in data['data']))
        relative_times = [
            entry[0]
            for entry in r_entries
        ]
        magnitudes = [
            entry[1]
            for entry in r_entries
        ]
    display_digits = schema.get('display_digits')
    magnitude_strings = [
        custom_format_number(magnitude, display_digits)
        for magnitude in magnitudes
    ]
    magnitude_average = None
    magnitude_stddev = None
    magnitude_min = None
    magnitude_max = None
    magnitude_count = None
    magnitude_first = None
    magnitude_last = None

    statistics = {'average', 'stddev'}
    if 'statistics' in schema:
        statistics = set(schema['statistics'])
    if 'min' in statistics:
        magnitude_min = np.min(magnitudes)
    if 'max' in statistics:
        magnitude_max = np.max(magnitudes)
    if 'count' in statistics:
        magnitude_count = len(magnitudes)
    if 'first' in statistics:
        magnitude_first = magnitudes[0]
    if 'last' in statistics:
        magnitude_last = magnitudes[-1]

    time_weights = np.zeros(len(magnitudes))
    # determine time-weighted average and standard deviation
    if 'average' in statistics or 'stddev' in statistics:
        if relative_times and len(relative_times) > 1:
            time_weights[0] = (relative_times[1] - relative_times[0]) / 2
            time_weights[-1] = (relative_times[-1] - relative_times[-2]) / 2
            for i in range(1, len(relative_times) - 1):
                rel_previous_time = relative_times[i - 1]
                rel_next_time = relative_times[i + 1]
                time_weights[i] = (rel_next_time - rel_previous_time) / 2
            magnitude_average = np.average(magnitudes, weights=time_weights)
            if 'stddev' in statistics:
                magnitude_stddev = np.sqrt(np.average(np.square(np.array(magnitudes) - magnitude_average), weights=time_weights))
            if 'average' not in statistics:
                magnitude_average = None
        elif len(utc_datetimes) > 1:
            time_weights[0] = (utc_datetimes[1] - utc_datetimes[0]).total_seconds() / 2
            time_weights[-1] = (utc_datetimes[-1] - utc_datetimes[-2]).total_seconds() / 2
            for i in range(1, len(utc_datetimes) - 1):
                previous_time = utc_datetimes[i - 1]
                next_time = utc_datetimes[i + 1]
                time_weights[i] = (next_time - previous_time).total_seconds() / 2
            magnitude_average = np.average(magnitudes, weights=time_weights)
            if 'stddev' in statistics:
                magnitude_stddev = np.sqrt(np.average(np.square(np.array(magnitudes) - magnitude_average), weights=time_weights))
            if 'average' not in statistics:
                magnitude_average = None
        else:
            if 'average' in statistics:
                magnitude_average = magnitudes[0]
    same_day = None
    if utc_datetimes:
        # convert datetimes to local timezone
        local_timezone = pytz.timezone(current_user.timezone or 'UTC')
        local_datetimes = [
            utc_datetime.astimezone(local_timezone)
            for utc_datetime in utc_datetimes
        ]
        time_strings = [
            local_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
            for local_datetime in local_datetimes
        ]
        same_day = utc_datetimes[0].date() == utc_datetimes[-1].date()
    else:
        time_strings = [
            custom_format_number(time, display_digits) + ' s'
            for time in relative_times
        ]
    return {
        'title': get_translated_text(schema.get('title')),
        'units': ' ' + prettify_units(data['units']) if data['dimensionality'] != 'dimensionless' else '',
        'relative_times': relative_times,
        'utc_datetimes': utc_datetimes,
        'times_strings': time_strings,
        'magnitudes': magnitudes,
        'magnitude_strings': magnitude_strings,
        'magnitude_average': magnitude_average,
        'magnitude_stddev': magnitude_stddev,
        'magnitude_min': magnitude_min,
        'magnitude_max': magnitude_max,
        'magnitude_count': magnitude_count,
        'magnitude_first': magnitude_first,
        'magnitude_last': magnitude_last,
        'same_day': same_day
    }


@JinjaFilter()
def to_timeseries_csv(
        rows: typing.List[typing.List[typing.Union[str, float]]]
) -> str:
    rows = copy.deepcopy(rows)
    user_timezone = pytz.timezone(current_user.timezone or 'UTC')
    if isinstance(rows[0][0], str):
        if user_timezone != pytz.utc:
            # convert datetimes from UTC if necessary
            for row in rows:
                try:
                    utc_datetime = datetime.strptime(typing.cast(str, row[0]), '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                local_datetime = utc_datetime.astimezone(user_timezone)
                row[0] = local_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
    csv_file = io.StringIO()
    writer = csv.writer(csv_file, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows(rows)
    return csv_file.getvalue()


@JinjaFilter()
def encode_choices(condition_list: list[dict[str, typing.Any]]) -> list[dict[str, typing.Any]]:
    for condition in condition_list:
        if condition['type'] == 'choice_equals':
            condition['encoded_choice'] = base64encode(condition['choice'])
        if condition['type'] == 'not':
            condition['condition'] = encode_choices([condition['condition']])[0]
        if condition['type'] in ('any', 'all'):
            condition['conditions'] = encode_choices(condition['conditions'])
    return condition_list


@JinjaFilter()
def stringify(json_object: list[dict[str, typing.Any]]) -> str:
    return json.dumps(json_object, separators=(',', ':'))


@JinjaFilter()
def unify_url(url: str) -> str:
    if not url.endswith('/'):
        url += '/'
    return url


@JinjaFunction()
def to_diff_table(
        lines_before: str,
        lines_after: str,
        label_before: str = '',
        label_after: str = ''
) -> str:
    return difflib.HtmlDiff(wrapcolumn=55).make_table(fromlines=lines_before.splitlines(), tolines=lines_after.splitlines(), fromdesc=label_before, todesc=label_after)


@JinjaFunction('get_component_by_uuid')
def safe_get_component_by_uuid(component_uuid: str) -> typing.Optional[Component]:
    try:
        return get_component_by_uuid(component_uuid=component_uuid)
    except errors.ComponentDoesNotExistError:
        return None


@JinjaFunction()
def get_property_names_in_order(
        schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Optional[typing.Dict[str, typing.Any]] = None
) -> typing.Sequence[str]:
    property_names = [
        property_name
        for property_name in schema.get('propertyOrder', [])
        if property_name in schema.get('properties', [])
    ] + [
        property_name
        for property_name in schema.get('properties', [])
        if property_name not in schema.get('propertyOrder', [])
    ]
    if previous_schema:
        for property_name in get_property_names_in_order(previous_schema):
            if property_name not in property_names:
                property_names.append(property_name)
    return property_names


@JinjaFunction()
def id_prefix_for_property_path(
        property_path: typing.Tuple[typing.Union[str, int], ...],
        id_prefix_root: str
) -> str:
    return '__'.join([
        str(path_element)
        for path_element in [id_prefix_root] + list(property_path)
    ]) + '_'


@JinjaFunction()
def is_deep_diff_possible(
        diff: DataDiff,
        schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any]
) -> bool:
    if '_before' in diff or '_after' in diff:
        return False
    if schema.get('type') == previous_schema.get('type') == 'array':
        if schema.get('style') != previous_schema.get('style'):
            return False
        if schema.get('style') == 'table' and schema.get('items', {}).get('type') != previous_schema.get('items', {}).get('type'):
            return False
    return True


@JinjaFunction()
def set_template_value(
        name: str,
        value: typing.Any
) -> None:
    if type(value) is jinja2.runtime.Undefined:
        # do not store undefined values, which will result in undefined as result in JavaScript
        return
    if not hasattr(flask.g, 'template_values'):
        flask.g.template_values = {}
    if flask.g.template_values is None:
        raise errors.TemplateValueError()
    if name in flask.g.template_values:
        raise errors.TemplateValueError()
    flask.g.template_values[name] = value


@JinjaFunction()
def get_template_values() -> typing.Any:
    if not hasattr(flask.g, 'template_values'):
        flask.g.template_values = {}
    template_values = flask.g.template_values
    flask.g.template_values = None
    return template_values


@JinjaFunction()
def current_utc_datetime() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


@JinjaFunction()
@cache_per_request()
def get_federated_identity(user: User | int) -> tuple[User, typing.Optional[User]]:
    if isinstance(user, int):
        user = get_user(user)
    if user is None:
        return user, None
    federated_user = get_user_by_federated_user(federated_user_id=user.id)
    if federated_user is not None:
        return federated_user, user
    return user, None


def build_modified_url(
        endpoint: str,
        blocked_parameters: typing.Sequence[str] = (),
        **query_parameters: typing.Any
) -> str:
    for param in flask.request.args:
        if param not in query_parameters:
            query_parameters[param] = flask.request.args.getlist(param)
    for param in blocked_parameters:
        if param in query_parameters:
            del query_parameters[param]
    return flask.url_for(
        endpoint,
        **query_parameters
    )


def parse_filter_id_params(
        params: werkzeug.datastructures.MultiDict[str, str],
        param_aliases: typing.List[str],
        valid_ids: typing.List[int],
        id_map: typing.Dict[str, int],
        multi_params_error: str,
        parse_error: str,
        invalid_id_error: str
) -> typing.Tuple[bool, typing.Optional[typing.List[int]]]:
    num_used_param_aliases = sum(param_alias in params for param_alias in param_aliases)
    if num_used_param_aliases == 0:
        return True, None
    if num_used_param_aliases > 1:
        flask.flash(multi_params_error, 'error')
        return False, None
    try:
        filter_ids = set()
        for param_alias in param_aliases:
            for ids_str in params.getlist(param_alias):
                for id_str in ids_str.split(','):
                    id_str = id_str.strip()
                    if not id_str:
                        continue
                    if id_str in id_map:
                        filter_ids.add(id_map[id_str])
                    else:
                        filter_ids.add(int(id_str))
    except ValueError:
        flask.flash(parse_error, 'error')
        return False, None
    if any(id not in valid_ids for id in filter_ids):
        flask.flash(invalid_id_error, 'error')
        return False, None
    if not filter_ids:
        return True, None
    return True, list(filter_ids)


@JinjaFilter()
def timeline_array_to_plotly_chart(
        timeline_array: typing.List[typing.Dict[str, typing.Any]]
) -> typing.Dict[str, typing.Any]:
    utc_datetime_strings = []
    for item in timeline_array:
        utc_datetime_strings.append(item['datetime']['utc_datetime'])
    markers = []
    max_concurrent_count = 1
    for index, item in enumerate(timeline_array):
        utc_datetime_string = item['datetime']['utc_datetime']
        concurrent_item_count = utc_datetime_strings.count(utc_datetime_string)
        utc_datetime = datetime.strptime(utc_datetime_string, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        local_datetime = utc_datetime.astimezone(pytz.timezone(current_user.timezone or 'UTC'))
        local_datetime_string = local_datetime.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(item.get('label'), dict) and item['label'].get('_type') == 'text' and not item['label'].get('multiline') and not item['label'].get('markdown') and get_translated_text(item['label'].get('text', '')).strip():
            label = typing.cast(str, markupsafe.escape(get_translated_text(item['label'].get('text', '')).strip()))
        else:
            label = format_datetime(local_datetime, format='medium')
        if concurrent_item_count > 1:
            max_concurrent_count = max(max_concurrent_count, concurrent_item_count)
            concurrent_item_index = utc_datetime_strings[:index].count(utc_datetime_string)
            markers.append((local_datetime_string, concurrent_item_index, label))
        else:
            markers.append((local_datetime_string, 0, label))
    plotly_chart = {
        "data": [
            {
                "x": [
                    marker[0]
                    for marker in markers
                ],
                "y": [
                    str(marker[1])
                    for marker in markers
                ],
                "text": [
                    marker[2]
                    for marker in markers
                ],
                "mode": "markers+text",
                "hoverinfo": "none",
                "textposition": "top center",
                "type": "scatter"
            }
        ],
        "layout": {
            "font": {
                "family": "Arial, sans-serif",
                "size": 12,
                "color": "#000"
            },
            "showlegend": False,
            "autosize": False,
            "width": 800,
            "height": 175 + 25 * max_concurrent_count,
            "xaxis": {
                "showgrid": False
            },
            "yaxis": {
                "showgrid": False,
                "zeroline": True,
                "showticklabels": False,
                "range": [
                    -0.5,
                    max_concurrent_count
                ]
            },
            "margin": {
                "l": 70,
                "r": 40,
                "b": 60,
                "t": 60,
                "pad": 2,
                "autoexpand": True
            },
            "dragmode": "pan",
            "paper_bgcolor": "#fff",
            "plot_bgcolor": "#fff",
            "hovermode": "closest",
            "separators": ".,"
        }
    }
    return plotly_chart


@JinjaFunction()
def get_action_type_ids_with_usable_actions() -> typing.Set[int]:
    action_type_ids_with_usable_actions = set()
    if current_user.is_authenticated and not current_user.is_readonly:
        actions = get_actions_with_permissions(current_user.id, permissions=Permissions.READ)
        for action in actions:
            if action.type is None:
                continue
            if action.admin_only and not current_user.is_admin:
                continue
            if action.disable_create_objects:
                continue
            if action.type.disable_create_objects:
                continue
            action_type_ids_with_usable_actions.add(action.type.id)
    return action_type_ids_with_usable_actions


@JinjaFunction()
def get_info_pages() -> typing.Sequence[InfoPage]:
    if not current_user.is_authenticated or current_user.is_readonly:
        return []
    return get_info_pages_for_endpoint(
        endpoint=flask.request.endpoint,
        user_id=current_user.id,
        exclude_disabled=True
    )
