# coding: utf-8
"""

"""
import csv
import datetime
import decimal
import functools
import io
import re
import typing

import babel
from flask_babel import _
from babel.numbers import parse_decimal
from flask_login import current_user
import pint
import pytz

from ...logic import schemas, languages
from ...logic.units import ureg, int_ureg
from ...logic.errors import ValidationError


class FormParserT(typing.Protocol):
    def __call__(
            self,
            form_data: typing.Dict[str, typing.List[str]],
            schema: typing.Dict[str, typing.Any],
            id_prefix: str,
            errors: typing.Dict[str, str],
            *,
            file_names_by_id: typing.Dict[int, str],
            required: bool = False,
            previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
    ) -> typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]]:
        ...


def form_data_parser(func: FormParserT) -> FormParserT:
    @functools.wraps(func)
    def wrapper(
            form_data: typing.Dict[str, typing.List[str]],
            schema: typing.Dict[str, typing.Any],
            id_prefix: str,
            errors: typing.Dict[str, str],
            *,
            file_names_by_id: typing.Dict[int, str],
            required: bool = False,
            previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
    ) -> typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]]:
        try:
            return func(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
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
def parse_any_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]]:
    if schema.get('type') == 'object':
        return parse_object_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'array':
        return parse_array_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'text':
        return parse_text_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'sample':
        return parse_sample_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'measurement':
        return parse_measurement_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'object_reference':
        return parse_object_reference_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'datetime':
        return parse_datetime_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'bool':
        return parse_boolean_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'quantity':
        return parse_quantity_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'tags':
        return parse_tags_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'hazards':
        return parse_hazards_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'user':
        return parse_user_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'plotly_chart':
        return parse_plotly_chart_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'timeseries':
        return parse_timeseries_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    elif schema.get('type') == 'file':
        return parse_file_form_data(form_data, schema, id_prefix, errors, required=required, file_names_by_id=file_names_by_id, previous_data=previous_data)
    raise ValueError('invalid schema')


@form_data_parser
def parse_text_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys == [id_prefix + '__text']:
        text_list = form_data.get(id_prefix + '__text', [])
        text = text_list[0] if text_list else None
        if not text and not required:
            return None
        # an empty text should get a min length error from validation, but a
        # missing text can be omitted if there is a non-zero min length
        if text is None and schema.get('minLength', 0) > 0:
            return None
        if text is None:
            text = ""
        data: typing.Dict[str, typing.Any] = {
            '_type': 'text',
            'text': str(text)
        }
        # if choice was a dict turned to a string, restore it
        # also if the input and choice match if either the input or the choice is embedded in a language dict,
        # interpreting it as the english translation the corresponding choice is used
        for choice in schema.get('choices', []):
            if str(choice) == data['text'] or choice == {'en': data['text']} or data['text'] == {'en': choice}:
                data['text'] = choice
                break
    else:
        if not all(key.startswith(id_prefix + '__text_') for key in keys):
            raise ValueError('invalid text form data')
        if not keys:
            return None
        enabled_languages = form_data.get(id_prefix + '__text_languages', [])
        if 'en' not in enabled_languages and ('languages' not in schema or schema['languages'] == 'all' or 'en' in schema['languages']):
            enabled_languages.append('en')
        data = {
            '_type': 'text',
            'text': {}
        }
        for language in enabled_languages:
            text_list = form_data.get(id_prefix + '__text_' + language, [])
            text = text_list[0] if text_list else None
            if not text and not required:
                continue
            if text is None and schema.get('minLength', 0) > 0:
                return None
            if text is None:
                text = ""
            data['text'][language] = text
        if not data['text'] and not required:
            return None
    if schema.get('markdown'):
        data['is_markdown'] = True
    schemas.validate(data, schema, strict=True)
    return data


@form_data_parser
def parse_hazards_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if id_prefix + '__hasnohazards' not in keys:
        raise ValueError(_('Please select at least one hazard or confirm that the object poses no hazards.'))
    hasnohazards_str = form_data.get(id_prefix + '__hasnohazards', [''])[0]
    if hasnohazards_str == 'true':
        hasnohazards = True
    elif hasnohazards_str == 'false':
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
def parse_tags_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
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
    schemas.validate(data, schema, strict=True)
    return data


@form_data_parser
def parse_sample_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__oid']:
        raise ValueError('invalid sample form data')
    object_id_str = form_data.get(id_prefix + '__oid', [''])[0]
    if not object_id_str:
        if not required:
            return None
        else:
            raise ValueError(_('Please select a sample.'))
    try:
        object_id = int(object_id_str)
    except ValueError:
        raise ValueError('object_id must be int')
    if object_id == -1 and isinstance(previous_data, dict):
        data = previous_data
    else:
        data = {
            '_type': 'sample',
            'object_id': object_id
        }
    schemas.validate(data, schema, strict=True)
    return data


@form_data_parser
def parse_measurement_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__oid']:
        raise ValueError('invalid measurement form data')
    object_id_str = form_data.get(id_prefix + '__oid', [''])[0]
    if not object_id_str:
        if not required:
            return None
        else:
            raise ValueError(_('Please select a measurement.'))
    try:
        object_id = int(object_id_str)
    except ValueError:
        raise ValueError('object_id must be int')
    if object_id == -1 and isinstance(previous_data, dict):
        data = previous_data
    else:
        data = {
            '_type': 'measurement',
            'object_id': object_id
        }
    schemas.validate(data, schema, strict=True)
    return data


@form_data_parser
def parse_object_reference_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__oid']:
        raise ValueError('invalid object reference form data')
    object_id_str = form_data.get(id_prefix + '__oid', [''])[0]
    if not object_id_str:
        if not required:
            return None
        else:
            raise ValueError(_('Please select an object reference.'))
    try:
        object_id = int(object_id_str)
    except ValueError:
        raise ValueError('object_id must be int')
    if object_id == -1 and isinstance(previous_data, dict):
        data = previous_data
    else:
        data = {
            '_type': 'object_reference',
            'object_id': object_id
        }
    schemas.validate(data, schema, strict=True)
    return data


@form_data_parser
def parse_quantity_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    # TODO: validate schema?
    if set(keys) != {id_prefix + '__magnitude', id_prefix + '__units'} and keys != [id_prefix + '__magnitude']:
        raise ValueError('invalid quantity form data')
    magnitude_str = form_data[id_prefix + '__magnitude'][0].strip()
    magnitude = None
    if not magnitude_str:
        if not required:
            return None
        else:
            raise ValueError(_('Please enter a magnitude.'))

    if id_prefix + '__units' in form_data:
        units = form_data[id_prefix + '__units'][0]
        try:
            pint_units = ureg.Unit(units)
        except pint.UndefinedUnitError:
            raise ValueError('invalid units')
    else:
        units = '1'
        pint_units = ureg.Unit('1')
    dimensionality = str(int_ureg.Unit(pint_units).dimensionality)
    user_locale = languages.get_user_language(current_user).lang_code
    if units in ['min', 'h'] and ':' in magnitude_str:
        if units == 'min':
            match = re.match(re.compile(
                r'^(?P<minutes>[0-9]+):'
                r'(?P<seconds>[0-5][0-9]([' + babel.Locale(user_locale).number_symbols['latn']['decimal'] + '][0-9]+)?)$'
            ), magnitude_str)
        else:
            match = re.match(re.compile(
                r'^(?P<hours>([0-9]+)):'
                r'(?P<minutes>[0-5][0-9])'
                r'(:(?P<seconds>[0-5][0-9]([' + babel.Locale(user_locale).number_symbols['latn']['decimal'] + '][0-9]+)?))?$'
            ), magnitude_str)
        if match is None:
            raise ValueError(_('Unable to parse time.'))

        match_dict = match.groupdict()
        try:
            if 'hours' in match_dict.keys():
                hours = int(match_dict['hours'])
            else:
                hours = 0
            minutes = int(match_dict['minutes'])
            if match_dict['seconds']:
                seconds = parse_decimal(match_dict['seconds'], locale=user_locale, strict=True)
            else:
                seconds = decimal.Decimal(0)
        except ValueError:
            raise ValueError(_('Unable to parse time.'))
        magnitude_in_base_units = float(hours * 3600 + minutes * 60 + seconds)
        data = {
            '_type': 'quantity',
            'magnitude_in_base_units': magnitude_in_base_units,
            'dimensionality': dimensionality,
            'units': units
        }
    else:
        try:
            if magnitude is None and re.fullmatch('[-]?[0-9]+', magnitude_str):
                try:
                    magnitude = decimal.Decimal(int(magnitude_str))
                except ValueError:
                    pass
            if magnitude is None:
                try:
                    magnitude = parse_decimal(magnitude_str, locale=user_locale, strict=True)
                except Exception:
                    pass
            if magnitude is None:
                raise ValueError(_('Unable to parse magnitude.'))
        except ValueError:
            raise ValueError(_('The magnitude must be a number.'))
        magnitude_in_base_units = float(ureg.Quantity(magnitude, pint_units).to_base_units().magnitude)
        data = {
            '_type': 'quantity',
            'magnitude_in_base_units': magnitude_in_base_units,
            'magnitude': float(magnitude),
            'dimensionality': dimensionality,
            'units': units
        }
    schemas.validate(data, schema, strict=True)
    return data


@form_data_parser
def parse_datetime_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    # TODO: validate schema?
    if keys != [id_prefix + '__datetime']:
        raise ValueError('invalid datetime form data')
    datetime_string = form_data.get(id_prefix + '__datetime', [''])[0]
    if not datetime_string:
        if not required:
            return None
        else:
            raise ValueError(_('Please enter a valid datetime.'))
    try:
        language = languages.get_user_language(current_user)
        parsed_datetime = datetime.datetime.strptime(datetime_string, language.datetime_format_datetime)
        # convert datetime to utc
        local_datetime = pytz.timezone(current_user.timezone or 'UTC').localize(parsed_datetime)
        utc_datetime = local_datetime.astimezone(pytz.utc)
        utc_datetime_str = utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        raise ValueError(_('Please enter a valid datetime.'))
    data = {
        '_type': 'datetime',
        'utc_datetime': utc_datetime_str
    }
    schemas.validate(data, schema, strict=True)
    return data


@form_data_parser
def parse_boolean_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
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
def parse_array_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str, errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.List[typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if not keys:
        return None
    item_schema = schema['items']
    item_indices = set()
    for key in keys:
        key_rest = key.replace(id_prefix, '', 1)
        if key_rest == '__hidden':
            continue
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
    items: typing.List[typing.Any] = []
    if item_indices:
        for i in item_indices:
            item_id_prefix = f'{id_prefix}__{i}'
            previous_item_data = previous_data[i] if isinstance(previous_data, list) and i < len(previous_data) else None
            items.append(parse_any_form_data(form_data, item_schema, item_id_prefix, errors, required=True, file_names_by_id=file_names_by_id, previous_data=previous_item_data))
    if not items and not required and schema.get('minItems', 0) > 0:
        return None
    schemas.validate(items, schema, strict=True, file_names_by_id=file_names_by_id)
    return items


@form_data_parser
def parse_object_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    assert schema['type'] == 'object'
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if not keys:
        return None
    data = {}
    for property_name, property_schema in schema['properties'].items():
        property_id_prefix = id_prefix + '__' + property_name
        property_required = property_name in schema.get('required', [])
        if isinstance(previous_data, dict) and property_name in previous_data:
            previous_property_data = previous_data[property_name]
        else:
            previous_property_data = None
        property = parse_any_form_data(form_data, property_schema, property_id_prefix, errors, required=property_required, file_names_by_id=file_names_by_id, previous_data=previous_property_data)
        if property is not None:
            data[property_name] = property
    schemas.validate(data, schema, strict=True, file_names_by_id=file_names_by_id)
    return data


@form_data_parser
def parse_user_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__uid']:
        raise ValueError('invalid user form data')
    user_id_str = form_data.get(id_prefix + '__uid', [''])[0]
    if not user_id_str:
        if not required:
            return None
        else:
            raise ValueError(_('Please select a user.'))
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise ValueError('user_id must be int')
    data = {
        '_type': 'user',
        'user_id': user_id
    }
    schemas.validate(data, schema, strict=True)
    return data


@form_data_parser
def parse_plotly_chart_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    plotly_chart_data_list = form_data.get(id_prefix + '__plotly', [])
    plotly_chart_data: typing.Optional[typing.Union[str, typing.Dict[str, typing.Any]]] = plotly_chart_data_list[0] if plotly_chart_data_list else None
    if plotly_chart_data is None and not required:
        plotly_chart_data = {}
    data = {
        '_type': 'plotly_chart',
        'plotly': plotly_chart_data
    }
    schemas.validate(data, schema, strict=True)

    return data


@form_data_parser
def parse_timeseries_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if set(keys) != {id_prefix + '__data', id_prefix + '__units'}:
        raise ValueError('invalid timeseries form data')
    units = form_data[id_prefix + '__units'][0]
    try:
        ureg.Unit(units)
    except pint.UndefinedUnitError:
        raise ValueError('invalid units')
    timeseries_data_str = form_data.get(id_prefix + '__data', [''])[0]
    if not timeseries_data_str and not required:
        return None
    timeseries_data: typing.List[typing.List[typing.Union[str, int, float]]]
    if not timeseries_data_str:
        timeseries_data = []
    else:
        csv_file = io.StringIO(timeseries_data_str)
        reader = csv.reader(csv_file, quoting=csv.QUOTE_NONNUMERIC)
        # csv.QUOTE_NONNUMERIC enables data conversion, however type annotations do not reflect this
        timeseries_data = list(reader)  # type: ignore
        if timeseries_data and all(isinstance(value, str) for value in timeseries_data[0]):
            # skip header rows
            timeseries_data = timeseries_data[1:]
        if not timeseries_data:
            raise ValueError(_('invalid timeseries CSV data, expected datetime string or relative time in seconds, magnitude and (optional) magnitude in base units'))
        is_relative_time = len(timeseries_data[0]) > 0 and type(timeseries_data[0][0]) in (int, float)
        user_timezone = pytz.timezone(current_user.timezone or 'UTC')
        for row in timeseries_data:
            if len(row) not in [2, 3] or not ((not is_relative_time and isinstance(row[0], str)) or (is_relative_time and type(row[0]) in (float, int))) or not all(type(entry) in (float, int) for entry in row[1:]):
                raise ValueError(_('invalid timeseries CSV data, expected datetime string or relative time in seconds, magnitude and (optional) magnitude in base units'))
            if not is_relative_time:
                try:
                    parsed_datetime = datetime.datetime.strptime(typing.cast(str, row[0]), '%Y-%m-%d %H:%M:%S.%f')
                except ValueError as exc:
                    raise ValueError(_('invalid datetime in timeseries, expected format: YYYY-MM-DD hh:mm:ss.ffffff')) from exc
                if user_timezone != pytz.utc:
                    # convert datetimes to UTC if necessary
                    try:
                        local_datetime = user_timezone.localize(parsed_datetime)
                        utc_datetime = local_datetime.astimezone(pytz.utc)
                    except Exception as exc:
                        raise ValueError(_('unable to convert datetime from your timezone to UTC')) from exc
                    row[0] = utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
    data = {
        '_type': 'timeseries',
        'data': timeseries_data,
        'units': units
    }
    schemas.validate(data, schema, strict=True)

    return data


@form_data_parser
def parse_file_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        id_prefix: str,
        errors: typing.Dict[str, str],
        *,
        file_names_by_id: typing.Dict[int, str],
        required: bool = False,
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    keys = [key for key in form_data.keys() if key.startswith(id_prefix + '__')]
    if keys != [id_prefix + '__file_id']:
        raise ValueError('invalid file form data')
    file_id_str = form_data.get(id_prefix + '__file_id', [''])[0]
    if not file_id_str:
        if not required:
            return None
        else:
            raise ValueError(_('Please select a file.'))
    try:
        file_id = int(file_id_str)
    except ValueError:
        raise ValueError(_('Please select a file.'))
    if file_id not in file_names_by_id:
        raise ValueError(_('Please select a file.'))
    if 'extensions' in schema:
        file_name = file_names_by_id[file_id]
        if not any(file_name.lower().endswith(extension.lower()) for extension in schema['extensions']):
            raise ValueError(_('Please select a file with one of these extensions: %(extensions)s', extensions=', '.join(schema['extensions'])))
    data = {
        '_type': 'file',
        'file_id': file_id
    }
    schemas.validate(data, schema, strict=True, file_names_by_id=file_names_by_id)
    return data


def parse_form_data(
        form_data: typing.Dict[str, typing.List[str]],
        schema: typing.Dict[str, typing.Any],
        *,
        file_names_by_id: typing.Dict[int, str],
        previous_data: typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]] = None
) -> typing.Tuple[typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]], typing.Dict[str, str]]:
    id_prefix = 'object'
    errors: typing.Dict[str, str] = {}
    data = parse_object_form_data(form_data, schema, id_prefix, errors, file_names_by_id=file_names_by_id, previous_data=previous_data)
    return data, errors
