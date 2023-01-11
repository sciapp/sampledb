# coding: utf-8
"""

"""
import dataclasses
import json
import base64
import functools
import hashlib
import typing
from io import BytesIO
import os
import re
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
from ..logic.components import get_component_or_none, get_component_id_by_uuid, get_component_by_uuid, Component
from ..logic.datatypes import Quantity
from ..logic.errors import UserIsReadonlyError
from ..logic.units import prettify_units
from ..logic.notifications import get_num_notifications
from ..logic.markdown_to_html import markdown_to_safe_html
from ..logic.users import get_user, User
from ..logic.utils import get_translated_text, get_all_translated_texts, show_admin_local_storage_warning, show_load_objects_in_background_warning, show_numeric_tags_warning
from ..logic.schemas.conditions import are_conditions_fulfilled
from ..logic.schemas.utils import get_property_paths_for_schema
from ..logic.actions import Action, ActionType
from ..logic.instruments import Instrument
from ..logic.action_permissions import get_sorted_actions_for_user
from ..logic.languages import get_user_language
from ..logic.locations import Location, LocationType, get_location, get_unhandled_object_responsibility_assignments, is_full_location_tree_hidden, get_locations_tree
from ..logic.location_permissions import get_user_location_permissions, get_locations_with_user_permissions
from ..logic.datatypes import JSONEncoder
from ..logic.security_tokens import generate_token
from ..logic.object_permissions import get_user_object_permissions, Permissions
from ..logic.objects import get_object, Object
from ..logic.groups import Group, get_groups
from ..logic.projects import Project, get_projects, get_child_project_ids, get_parent_project_ids, get_project
from ..logic.group_categories import get_group_category_tree, get_group_categories, get_basic_group_categories, get_project_group_categories, get_full_group_category_name


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
jinja_function()(get_component_id_by_uuid)
jinja_function()(get_unhandled_object_responsibility_assignments)
jinja_function()(is_full_location_tree_hidden)


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
    if file.storage not in {'local', 'database', 'federation'}:
        return False
    file_name = file.original_file_name
    file_extension = os.path.splitext(file_name)[1]
    return file_extension in flask.current_app.config.get('MIME_TYPES', {})


def file_name_is_image(file_name):
    file_extension = os.path.splitext(file_name)[1]
    return flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, '').startswith('image/')


@jinja_filter()
def is_image(file):
    # federation files are not recognized as images to prevent loading their thumbnails from other database
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


@jinja_filter('generic_format_datetime')
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
def custom_format_number(
    number: typing.Union[str, int, float],
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
    if not disable_scientific_format:
        if number == 0:
            exponent = 0
        else:
            exponent = int(floor(log10(abs(number))))

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

        if display_digits < 0:
            display_digits = 0
        if display_digits > 27:
            display_digits = 27

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
        with numbers.decimal.localcontext() as ctx:
            ctx.prec = 15
            return numbers.format_decimal(
                numbers.decimal.Decimal(number),
                locale=locale,
                format=f,
                decimal_quantization=False
            )


@jinja_filter('format_time')
def format_time(
    magnitude_in_base_units: float,
    units: str,
    display_digits: typing.Optional[int] = None
):
    if units not in {'min', 'h'}:
        raise errors.MismatchedUnitError()
    decimal = 0
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


@jinja_filter('format_quantity')
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
    if data.get('units') in {'h', 'min'}:
        return f'{format_time(magnitude, data.get("units"), schema.get("display_digits"))}{narrow_non_breaking_space}{data.get("units")}'
    quantity = Quantity.from_json(data)
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
        user_language = get_user_language(flask_login.current_user)
        local_datetime = datetime.strptime(datetime_input, user_language.datetime_format_datetime)
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
        has_read_permissions = Permissions.READ in get_user_location_permissions(location_id, flask_login.current_user.id)

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


@jinja_filter()
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
        if action.type_id is not None and action.type.is_template and action.schema
    ]


@jinja_function()
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
        if not action.schema:
            continue
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
        show_numeric_tags_warning(),
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


@jinja_function()
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


@jinja_function()
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


@jinja_function()
def get_object_name_if_user_has_permissions(object_id: int) -> str:
    fallback_name = f"{flask_babel.gettext('Object')} #{object_id}"
    try:
        permissions = get_user_object_permissions(object_id, flask_login.current_user.id)
        if Permissions.READ in permissions:
            object = get_object(object_id)
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
    if not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{4}', orcid, flags=re.ASCII):
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

        def get_name(self):
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


@jinja_function()
@dataclasses.dataclass(frozen=True)
class FederationObjectRef(FederationRef):
    referenced_class: typing.Type[Object] = Object


@jinja_function()
@dataclasses.dataclass(frozen=True)
class FederationUserRef(FederationRef):
    referenced_class: typing.Type[User] = User


@jinja_function()
def get_federation_url(obj: typing.Any) -> str:
    component_address = obj.component.address
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
        for location in get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
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
        (location_id, '', locations_tree[location_id], [location_id])
        for location_id in locations_tree
    ]
    while unvisited_location_ids_prefixes_and_subtrees:
        location_id, name_prefix, subtree, id_path = unvisited_location_ids_prefixes_and_subtrees.pop(0)
        location = locations_map[location_id]
        # skip hidden locations with a fully hidden subtree
        is_full_subtree_hidden = is_full_location_tree_hidden(readable_locations_map, subtree)
        if not flask_login.current_user.is_admin and location.is_hidden and is_full_subtree_hidden:
            continue
        has_read_permissions = location_id in readable_location_ids
        # skip unreadable locations, but allow processing their child locations
        # in case any of them are readable
        if has_read_permissions and (not location.is_hidden or flask_login.current_user.is_admin):
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


@jinja_function()
def get_user_or_none(user_id: int) -> typing.Optional[User]:
    try:
        return get_user(user_id)
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

    def _add_project_group_to_all_choices(id_path, name_prefix, group_id):
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

    def _fill_all_choices(id_path, name_prefix, group_category_id, group_category_tree):
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


@jinja_function()
def get_basic_group_name_prefixes(group_id: int) -> typing.List[str]:
    group_categories = get_basic_group_categories(group_id)
    return sorted([
        ' / '.join(
            get_translated_text(category_name, default=flask_babel.gettext("Unnamed Category"))
            for category_name in get_full_group_category_name(group_category.id)
        ) + ' / '
        for group_category in group_categories
    ])


@jinja_function()
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
