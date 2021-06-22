# coding: utf-8
"""

"""

import datetime
import functools

from flask_babel import _
from babel.numbers import parse_number, parse_decimal
from flask_login import current_user
import pint
import pytz

from ..logic import schemas, languages
from ..logic.settings import get_user_settings
from ..logic.units import ureg
from ..logic.errors import ValidationError
from ..logic.schemas.generate_placeholder import generate_placeholder


def form_data_parser(func):
    @functools.wraps(func)
    def wrapper(form_data, schema, id_prefix, errors, required=False):
        try:
            return func(form_data, schema, id_prefix, errors, required=required)
        except ValueError as e:
            for name in form_data:
                if name.startswith(id_prefix) and '__' not in name[len(id_prefix) + 1:]:
                    errors[name] = str(e)
            return None
        except ValidationError as e:
            for name in form_data:
                if name.startswith(id_prefix) and '__' not in name[len(id_prefix) + 1:]:
                    errors[name] = e.message
            return None
    return wrapper


@form_data_parser
def parse_any_form_data(form_data, schema, id_prefix, errors, required=False):
    if schema.get('type') == 'object':
        return parse_object_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'array':
        return parse_array_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'text':
        return parse_text_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'sample':
        return parse_sample_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'measurement':
        return parse_measurement_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'object_reference':
        return parse_object_reference_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'datetime':
        return parse_datetime_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'bool':
        return parse_boolean_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'quantity':
        return parse_quantity_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'tags':
        return parse_tags_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'hazards':
        return parse_hazards_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'user':
        return parse_user_form_data(form_data, schema, id_prefix, errors, required=required)
    elif schema.get('type') == 'plotly_chart':
        return parse_plotly_chart_form_data(form_data, schema, id_prefix, errors, required=required)
    raise ValueError('invalid schema')


@form_data_parser
def parse_text_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys == [id_prefix + '__text']:
        text = form_data.get(id_prefix + '__text', [None])[0]
        if not text and not required:
            return None
        if text is None:
            text = ""
        data = {
            '_type': 'text',
            'text': str(text)
        }
        # if choice was a dict turned to a string, restore it
        for choice in schema.get('choices', []):
            if str(choice) == data['text']:
                data['text'] = choice
                break
    else:
        if not all(key.startswith(id_prefix + '__text_') for key in keys):
            raise ValueError('invalid text form data')
        enabled_languages = form_data.get(id_prefix + '__text_languages', [])
        if 'en' not in enabled_languages:
            enabled_languages.append('en')
        data = {
            '_type': 'text',
            'text': {}
        }
        for language in enabled_languages:
            text = form_data.get(id_prefix + '__text_' + language, [None])[0]
            if not text and not required:
                continue
            if text is None:
                text = ""
            data['text'][language] = text
        if not data['text'] and not required:
            return None
    if schema.get('markdown'):
        data['is_markdown'] = True
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_hazards_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if id_prefix + '__hasnohazards' not in keys:
        raise ValueError(_('Please select at least one hazard or confirm that the object poses no hazards.'))
    hasnohazards = form_data.get(id_prefix + '__hasnohazards', [''])[0]
    if hasnohazards == 'true':
        hasnohazards = True
    elif hasnohazards == 'false':
        hasnohazards = False
    else:
        raise ValueError('invalid hazards form data')
    available_hazards = {
        'ghs01': 1, 'ghs02': 2, 'ghs03': 3, 'ghs04': 4, 'ghs05': 5, 'ghs06': 6, 'ghs07': 7, 'ghs08': 8, 'ghs09': 9
    }
    hazards = []
    for key in keys:
        if key == id_prefix + '__hasnohazards':
            continue
        if key == id_prefix + '__hidden':
            continue
        hazard_name = key.rsplit('__', 1)[1]
        if hazard_name in available_hazards:
            hazards.append(available_hazards[hazard_name])
        else:
            raise ValueError('invalid hazards form data')
    if hasnohazards != (len(hazards) == 0):
        raise ValueError(_('Please select at least one hazard or confirm that the object poses no hazards.'))
    data = {
        '_type': 'hazards',
        'hazards': hazards
    }
    return data


@form_data_parser
def parse_tags_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__tags']:
        raise ValueError('invalid tags form data')
    text = form_data.get(id_prefix + '__tags', [''])[0]
    tags = [tag.lower() for tag in text.split(',')]
    unique_tags = []
    for tag in tags:
        tag = ''.join(c for c in tag if not c.isspace())
        if not tag:
            continue
        if tag not in unique_tags:
            unique_tags.append(tag)
    tags = unique_tags
    data = {
        '_type': 'tags',
        'tags': tags
    }
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_sample_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__oid']:
        raise ValueError('invalid sample form data')
    object_id = form_data.get(id_prefix + '__oid', [''])[0]
    if not object_id:
        if not required:
            return None
        else:
            raise ValueError(_('Please select a sample.'))
    try:
        object_id = int(object_id)
    except ValueError:
        raise ValueError('object_id must be int')
    data = {
        '_type': 'sample',
        'object_id': object_id
    }
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_measurement_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__oid']:
        raise ValueError('invalid measurement form data')
    object_id = form_data.get(id_prefix + '__oid', [''])[0]
    if not object_id:
        if not required:
            return None
        else:
            raise ValueError(_('Please select a measurement.'))
    try:
        object_id = int(object_id)
    except ValueError:
        raise ValueError('object_id must be int')
    data = {
        '_type': 'measurement',
        'object_id': object_id
    }
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_object_reference_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__oid']:
        raise ValueError('invalid object reference form data')
    object_id = form_data.get(id_prefix + '__oid', [''])[0]
    if not object_id:
        if not required:
            return None
        else:
            raise ValueError(_('Please select an object reference.'))
    try:
        object_id = int(object_id)
    except ValueError:
        raise ValueError('object_id must be int')
    data = {
        '_type': 'object_reference',
        'object_id': object_id
    }
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_quantity_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    # TODO: validate schema?
    if set(keys) != {id_prefix + '__magnitude', id_prefix + '__units'} and keys != [id_prefix + '__magnitude']:
        raise ValueError('invalid quantity form data')
    magnitude = form_data[id_prefix + '__magnitude'][0].strip()
    if not magnitude:
        if not required:
            return None
        else:
            raise ValueError(_('Please enter a magnitude.'))
    try:
        if isinstance(magnitude, str):
            user_locale = languages.get_user_language(current_user).lang_code
            try:
                magnitude = parse_number(magnitude, locale=user_locale)
            except ValueError:
                try:
                    magnitude = parse_decimal(magnitude, locale=user_locale)
                except ValueError:
                    raise ValueError(_('Unable to parse magnitude.'))
        magnitude = float(magnitude)
    except ValueError:
        raise ValueError(_('The magnitude must be a number.'))
    if id_prefix + '__units' in form_data:
        units = form_data[id_prefix + '__units'][0]
        try:
            pint_units = ureg.Unit(units)
        except pint.UndefinedUnitError:
            raise ValueError('invalid units')
    else:
        units = '1'
        pint_units = ureg.Unit('1')
    dimensionality = str(pint_units.dimensionality)
    magnitude_in_base_units = ureg.Quantity(magnitude, pint_units).to_base_units().magnitude
    data = {
        '_type': 'quantity',
        'magnitude_in_base_units': magnitude_in_base_units,
        'dimensionality': dimensionality,
        'units': units
    }
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_datetime_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    # TODO: validate schema?
    if keys != [id_prefix + '__datetime']:
        raise ValueError('invalid datetime form data')
    datetime_string = form_data.get(id_prefix + '__datetime', [''])[0]
    try:
        settings = get_user_settings(current_user.id)
        language = languages.get_user_language(current_user)
        parsed_datetime = datetime.datetime.strptime(datetime_string, language.datetime_format_datetime)
        # convert datetime to utc
        local_datetime = pytz.timezone(settings['TIMEZONE']).localize(parsed_datetime)
        utc_datetime = local_datetime.astimezone(pytz.utc)
        utc_datetime = utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        raise ValueError(_('Please enter a valid datetime.'))
    data = {
        '_type': 'datetime',
        'utc_datetime': utc_datetime
    }
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_boolean_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    # TODO: validate schema?
    if set(keys) == {id_prefix + '__hidden', id_prefix + '__value'}:
        value = True
    elif keys == [id_prefix + '__hidden']:
        value = False
    else:
        raise ValueError('invalid boolean form data')
    return {
        '_type': 'bool',
        'value': value
    }


@form_data_parser
def parse_array_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    item_schema = schema['items']
    item_indices = set()
    for key in keys:
        key_rest = key.replace(id_prefix, '', 1)
        if not key_rest.startswith('__'):
            raise ValueError('invalid array form data')
        key_parts = key_rest.split('__')
        if not key_parts[0] == '':
            raise ValueError('invalid array form data')
        try:
            item_index = int(key_parts[1])
        except ValueError:
            raise ValueError('invalid array form data')
        item_indices.add(item_index)
    items = []
    if item_indices:
        num_items = max([i for i in item_indices]) + 1
        for i in range(num_items):
            if i not in item_indices:
                items.append(None)
            else:
                item_id_prefix = id_prefix + '__{}'.format(i)
                items.append(parse_any_form_data(form_data, item_schema, item_id_prefix, errors, True))
        if None in items:
            # use a placeholder if form_data had no (valid) information on an
            # item, otherwise items would not be a valid array and the form
            # could not be submitted at all
            # if there is no valid placeholder, skip the missing items
            placeholder = generate_placeholder(item_schema)
            if placeholder is None:
                items = [
                    item
                    for item in items
                    if item is not None
                ]
            else:
                items = [
                    placeholder if item is None else item
                    for item in items
                ]
    schemas.validate(items, schema)
    return items


@form_data_parser
def parse_object_form_data(form_data, schema, id_prefix, errors, required=False):
    assert schema['type'] == 'object'
    data = {}
    if any(key.startswith(id_prefix + '__') for key in form_data.keys()):
        for property_name, property_schema in schema['properties'].items():
            property_id_prefix = id_prefix + '__' + property_name
            property_required = (property_name in schema.get('required', []))
            property = parse_any_form_data(form_data, property_schema, property_id_prefix, errors, required=property_required)
            if property is not None:
                data[property_name] = property
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_user_form_data(form_data, schema, id_prefix, errors, required=False):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__uid']:
        raise ValueError('invalid user form data')
    user_id = form_data.get(id_prefix + '__uid', [''])[0]
    if not user_id:
        if not required:
            return None
        else:
            raise ValueError(_('Please select a user.'))
    try:
        user_id = int(user_id)
    except ValueError:
        raise ValueError('user_id must be int')
    data = {
        '_type': 'user',
        'user_id': user_id
    }
    schemas.validate(data, schema)
    return data


@form_data_parser
def parse_plotly_chart_form_data(form_data, schema, id_prefix, errors, required=False):
    plotly_chart_data = form_data.get(id_prefix + '__plotly', [None])[0]
    if plotly_chart_data is None and not required:
        plotly_chart_data = {}
    data = {
        '_type': 'plotly_chart',
        'plotly': plotly_chart_data
    }
    schemas.validate(data, schema)

    return data


def parse_form_data(form_data, schema):
    id_prefix = 'object'
    errors = {}
    data = parse_object_form_data(form_data, schema, id_prefix, errors)
    return data, errors
