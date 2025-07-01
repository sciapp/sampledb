# coding: utf-8
"""
Implementation of validate(instance, schema)
"""

import re
import datetime
import decimal
import string
import typing
import math
import json

import plotly
from flask_babel import _
import flask

from .conditions import are_conditions_fulfilled
from ...logic import actions, objects, datatypes, users, languages
from ...models import ActionType
from ..errors import ObjectDoesNotExistError, ValidationError, ValidationMultiError, UserDoesNotExistError, InvalidURLError
from .utils import units_are_valid
from ..utils import get_translated_text, parse_url
from ..units import get_dimensionality_for_units, get_magnitude_in_base_units

OPT_IMPORT_KEYS = {'export_edit_note', 'component_uuid', 'eln_source_url', 'eln_object_url', 'eln_user_url'}


def validate(
        instance: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]],
        schema: typing.Dict[str, typing.Any],
        path: typing.Optional[typing.List[str]] = None,
        allow_disabled_languages: bool = False,
        strict: bool = False,
        file_names_by_id: typing.Optional[typing.Dict[int, str]] = None
) -> None:
    """
    Validates the given instance using the given schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :param allow_disabled_languages: whether disabled languages are allowed
    :param strict: whether the data should be evaluated in strict mode, or backwards compatible otherwise
    :param file_names_by_id: a dict mapping file IDs to file names, or None
    :raise ValidationError: if the schema is invalid.
    """
    if path is None:
        path = []
    if not isinstance(schema, dict):
        raise ValidationError('invalid schema (must be dict)', path)
    if 'type' not in schema:
        raise ValidationError('invalid schema (must contain type)', path)
    if schema['type'] == 'array' and isinstance(instance, list):
        return _validate_array(instance, schema, path, allow_disabled_languages=allow_disabled_languages, strict=strict, file_names_by_id=file_names_by_id)
    elif schema['type'] == 'object' and isinstance(instance, dict):
        return _validate_object(instance, schema, path, allow_disabled_languages=allow_disabled_languages, strict=strict, file_names_by_id=file_names_by_id)
    elif schema['type'] == 'text' and isinstance(instance, dict):
        return _validate_text(instance, schema, path, allow_disabled_languages=allow_disabled_languages)
    elif schema['type'] == 'datetime' and isinstance(instance, dict):
        return _validate_datetime(instance, schema, path)
    elif schema['type'] == 'bool' and isinstance(instance, dict):
        return _validate_bool(instance, schema, path)
    elif schema['type'] == 'quantity' and isinstance(instance, dict):
        return _validate_quantity(instance, schema, path)
    elif schema['type'] == 'sample' and isinstance(instance, dict):
        return _validate_sample(instance, schema, path)
    elif schema['type'] == 'measurement' and isinstance(instance, dict):
        return _validate_measurement(instance, schema, path)
    elif schema['type'] == 'object_reference' and isinstance(instance, dict):
        return _validate_object_reference(instance, schema, path)
    elif schema['type'] == 'tags' and isinstance(instance, dict):
        return _validate_tags(instance, schema, path, strict=strict)
    elif schema['type'] == 'hazards' and isinstance(instance, dict):
        return _validate_hazards(instance, schema, path)
    elif schema['type'] == 'user' and isinstance(instance, dict):
        return _validate_user(instance, schema, path)
    elif schema['type'] == 'plotly_chart' and isinstance(instance, dict):
        return _validate_plotly_chart(instance, schema, path)
    elif schema['type'] == 'timeseries' and isinstance(instance, dict):
        return _validate_timeseries(instance, schema, path)
    elif schema['type'] == 'file' and isinstance(instance, dict):
        return _validate_file(instance, schema, path, file_names_by_id=file_names_by_id)
    else:
        raise ValidationError('invalid type', path)


def _validate_array(
        instance: typing.List[typing.Any],
        schema: typing.Dict[str, typing.Any], path: typing.List[str],
        allow_disabled_languages: bool = False,
        strict: bool = False,
        file_names_by_id: typing.Optional[typing.Dict[int, str]] = None
) -> None:
    """
    Validates the given instance using the given array schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :param strict: whether the data should be evaluated in strict mode, or backwards compatible otherwise
    :param file_names_by_id: a dict mapping file IDs to file names, or None
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, list):
        raise ValidationError('instance must be list', path)
    if 'minItems' in schema and len(instance) < schema['minItems']:
        raise ValidationError(f'expected at least {schema["minItems"]} items', path)
    if 'maxItems' in schema and len(instance) > schema['maxItems']:
        raise ValidationError(f'expected at most {schema["maxItems"]} items', path)
    errors = []
    for index, item in enumerate(instance):
        try:
            validate(item, schema['items'], path + [str(index)], allow_disabled_languages=allow_disabled_languages, strict=strict, file_names_by_id=file_names_by_id)
        except ValidationError as e:
            errors.append(e)
    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        raise ValidationMultiError(errors)


def _validate_hazards(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validate the given instance using the given GHS hazards schema and raise a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    if path != ['hazards']:
        raise ValidationError('GHS hazards must be a top-level entry named "hazards"', path)
    valid_keys = {'_type', 'hazards'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'hazards':
        raise ValidationError('expected _type "hazards"', path)
    if not isinstance(instance['hazards'], list):
        raise ValidationError('hazards must be list', path)
    errors = []
    hazards = []
    for index, item in enumerate(instance['hazards']):
        if not isinstance(item, int):
            errors.append(ValidationError(f'invalid hazard index type: {type(item)}', path + ['hazards', str(index)]))
        elif item in hazards:
            errors.append(ValidationError(f'duplicate hazard index: {item}', path + ['hazards', str(index)]))
        elif item < 1 or item > 9:
            errors.append(ValidationError(f'invalid hazard index: {item}', path + ['hazards', str(index)]))
        else:
            hazards.append(item)

    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        raise ValidationMultiError(errors)


def _validate_tags(
        instance: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any], path: typing.List[str],
        strict: bool = False
) -> None:
    """
    Validates the given instance using the given tags schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :param strict: whether the data should be evaluated in strict mode, or backwards compatible otherwise
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'tags'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'tags':
        raise ValidationError('expected _type "tags"', path)
    if not isinstance(instance['tags'], list):
        raise ValidationError('tags must be list', path)
    errors = []
    tags = []
    for index, item in enumerate(instance['tags']):
        if not isinstance(item, str):
            errors.append(ValidationError(f'invalid tag type: {type(item)}', path + ['tags', str(index)]))
        elif item in tags:
            errors.append(ValidationError(f'duplicate tag: {item}', path + ['tags', str(index)]))
        elif item.lower() != item:
            errors.append(ValidationError(f'tag not lowercase: {item}', path + ['tags', str(index)]))
        elif any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-äöüß' for c in item):
            errors.append(ValidationError(f'tag contains invalid character: {item}', path + ['tags', str(index)]))
        elif strict and all(c in string.digits for c in item) and not flask.current_app.config['ENABLE_NUMERIC_TAGS']:
            errors.append(ValidationError('numeric tags are not supported', path + ['tags', str(index)]))
        else:
            tags.append(item)

    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        raise ValidationMultiError(errors)


def _validate_object(
        instance: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        allow_disabled_languages: bool = False,
        strict: bool = False,
        file_names_by_id: typing.Optional[typing.Dict[int, str]] = None
) -> None:
    """
    Validates the given instance using the given object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :param strict: whether the data should be evaluated in strict mode, or backwards compatible otherwise
    :param file_names_by_id: a dict mapping file IDs to file names, or None
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    errors = []

    properties_with_unfulfilled_conditions = []
    for property_name, property_schema in schema['properties'].items():
        if not are_conditions_fulfilled(property_schema.get('conditions'), instance):
            properties_with_unfulfilled_conditions.append(property_name)
            if property_name in instance or (property_name == 'name' and not path):
                errors.append(ValidationError(f'conditions for property "{property_name}" not fulfilled', path + [property_name]))

    if 'required' in schema:
        for property_name in schema['required']:
            if property_name in properties_with_unfulfilled_conditions:
                # this property must not be included, as its conditions are not fulfilled
                continue
            if property_name not in instance:
                errors.append(ValidationError(f'missing required property "{property_name}"', path + [property_name]))
    for property_name, property_value in instance.items():
        try:
            if property_name not in schema['properties']:
                raise ValidationError(f'unknown property "{property_name}"', path + [property_name])
            else:
                validate(property_value, schema['properties'][property_name], path + [property_name], allow_disabled_languages=allow_disabled_languages, strict=strict, file_names_by_id=file_names_by_id)
        except ValidationError as e:
            errors.append(e)
    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        raise ValidationMultiError(errors)


def _validate_text(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str], allow_disabled_languages: bool = False) -> None:
    """
    Validates the given instance using the given text object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'text'}
    required_keys = set(valid_keys)
    if schema.get('markdown', False):
        valid_keys.add('is_markdown')
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'text':
        raise ValidationError('expected _type "text"', path)
    if not isinstance(instance['text'], str) and not isinstance(instance['text'], dict):
        raise ValidationError('text must be str or a dictionary', path)
    choices = schema.get('choices', None)
    if choices:
        for choice in choices:
            if str(choice) == instance['text'] or choice == {'en': instance['text']} or instance['text'] == {'en': choice}:
                instance['text'] = choice
                break
        if instance['text'] not in choices:
            raise ValidationError(_('The text must be one of: %(choices)s.', choices=', '.join(get_translated_text(choice) for choice in choices)), path)
    min_length = schema.get('minLength', 0)
    max_length = schema.get('maxLength', None)

    if isinstance(instance['text'], str):
        if len(instance['text']) < min_length:
            raise ValidationError(_('The text must be at least %(min_length)s characters long.', min_length=min_length), path)
        if max_length is not None and len(instance['text']) > max_length:
            raise ValidationError(_('The text must be at most %(max_length)s characters long.', max_length=max_length), path)
    elif not choices:
        all_languages = languages.get_languages()
        language_names = {
            language.lang_code: get_translated_text(language.names)
            for language in all_languages
        }
        if 'languages' in schema:
            if schema['languages'] == 'all':
                allowed_language_codes = {
                    language.lang_code
                    for language in all_languages
                    if allow_disabled_languages or language.enabled_for_input
                }
            else:
                allowed_language_codes = {
                    language.lang_code
                    for language in all_languages
                    if allow_disabled_languages or (language.enabled_for_input and language.lang_code in schema['languages'])
                }
        else:
            allowed_language_codes = {'en'}
        for text in instance['text'].values():
            if not isinstance(text, str):
                raise ValidationError('The text in a translation dict must be str.', path)
            if len(text) < min_length:
                raise ValidationError(_('The text must be at least %(min_length)s characters long.', min_length=min_length), path)
            if max_length is not None and len(text) > max_length:
                raise ValidationError(_('The text must be at most %(max_length)s characters long.', max_length=max_length), path)
        for lang in instance['text'].keys():
            if lang not in allowed_language_codes:
                raise ValidationError(_('The language "%(lang_code)s" is not allowed for this field.', lang_code=language_names.get(lang, lang)), path)
    if 'pattern' in schema:
        if not isinstance(schema['pattern'], str):
            raise ValidationError('pattern must be str', path)
        if isinstance(instance['text'], dict):
            for text in instance['text'].values():
                if re.match(schema['pattern'], text) is None:
                    raise ValidationError(_('Input must match: %(pattern)s', pattern=schema['pattern']), path)
        if isinstance(instance['text'], str):
            if re.match(schema['pattern'], instance['text']) is None:
                raise ValidationError(_('Input must match: %(pattern)s', pattern=schema['pattern']), path)
    if 'is_markdown' in instance and not isinstance(instance['is_markdown'], bool):
        raise ValidationError('is_markdown must be bool', path)


def _validate_datetime(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validates the given instance using the given datetime object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'utc_datetime'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'datetime':
        raise ValidationError('expected _type "datetime"', path)
    if not isinstance(instance['utc_datetime'], str):
        raise ValidationError('utc_datetime must be str', path)
    try:
        datetime.datetime.strptime(instance['utc_datetime'], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise ValidationError(_('Please enter the date and time in the format: %(datetime_format)s', datetime_format='YYYY-MM-DD HH:MM:SS'), path)


def _validate_bool(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validates the given instance using the given boolean object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'value'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'bool':
        raise ValidationError('expected _type "bool"', path)
    if not isinstance(instance['value'], bool):
        raise ValidationError('value must be bool', path)


def _validate_quantity(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validates the given instance using the given quantity object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    required_keys = {'_type'}
    valid_keys = required_keys.union({'units', 'dimensionality', 'magnitude_in_base_units', 'magnitude'})
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'quantity':
        raise ValidationError('expected _type "quantity"', path)
    if 'units' not in instance:
        if not isinstance(schema['units'], str):
            raise ValidationError('missing unambiguous units for quantity property with multiple possible units', path)
        instance['units'] = schema['units']
    if not isinstance(instance['units'], str):
        raise ValidationError('units must be str', path)
    if not units_are_valid(instance['units']):
        raise ValidationError('Invalid/Unknown units', path)
    try:
        if isinstance(schema['units'], str):
            schema_units = schema['units']
        else:
            schema_units = schema['units'][0]
        schema_quantity = datatypes.Quantity(1.0, units=schema_units)
    except Exception:
        raise ValidationError('Unable to create schema quantity', path)

    quantity_magnitude = None
    quantity_magnitude_in_base_units = None

    if 'magnitude' in instance:
        if not isinstance(instance['magnitude'], float) and not isinstance(instance['magnitude'], int):
            raise ValidationError('magnitude must be float or int', path)
        if not math.isfinite(instance['magnitude']):
            raise ValidationError('magnitude must be a finite number', path)
        try:
            quantity_magnitude = datatypes.Quantity(instance['magnitude'], units=instance['units'],
                                                    already_in_base_units=False)
        except Exception:
            raise ValidationError('Unable to create quantity based on given magnitude', path)
    if 'magnitude_in_base_units' in instance:
        if not isinstance(instance['magnitude_in_base_units'], float) and not isinstance(instance['magnitude_in_base_units'], int):
            raise ValidationError('magnitude_in_base_units must be float or int', path)
        if not math.isfinite(instance['magnitude_in_base_units']):
            raise ValidationError('magnitude_in_base_units must be a finite number', path)
        try:
            quantity_magnitude_in_base_units = datatypes.Quantity(instance['magnitude_in_base_units'], units=instance['units'], already_in_base_units=True)
        except Exception:
            raise ValidationError('Unable to create quantity based on given magnitude_in_base_units', path)

    if quantity_magnitude is not None and quantity_magnitude_in_base_units is not None and not (
            math.isclose(quantity_magnitude.magnitude, quantity_magnitude_in_base_units.magnitude) or
            math.isclose(quantity_magnitude.magnitude_in_base_units, quantity_magnitude_in_base_units.magnitude_in_base_units)
    ):
        raise ValidationError('magnitude and magnitude_in_base_units do not match, either set only one or make sure both match', path)
    if quantity_magnitude is None:
        if quantity_magnitude_in_base_units is None:
            raise ValidationError('missing keys in schema: either magnitude or magnitude_in_base_units has to be given', path)
        quantity_magnitude = quantity_magnitude_in_base_units

    if 'min_magnitude' in schema and quantity_magnitude.magnitude_in_base_units < schema['min_magnitude']:
        min_magnitude = datatypes.Quantity(schema["min_magnitude"], units=schema['units'], already_in_base_units=True).magnitude
        min_value = f'{min_magnitude}{" " + schema["units"] if schema["units"] != "1" else ""}'
        raise ValidationError(_('Must be greater than or equal to %(value)s', value=min_value), path)

    if 'max_magnitude' in schema and quantity_magnitude.magnitude_in_base_units > schema['max_magnitude']:
        max_magnitude = datatypes.Quantity(schema["max_magnitude"], units=schema['units'], already_in_base_units=True).magnitude
        max_value = f'{max_magnitude}{" " + schema["units"] if schema["units"] != "1" else ""}'
        raise ValidationError(_('Must be less than or equal to %(value)s', value=max_value), path)

    # automatically add dimensionality and either magnitude oder magnitude_in_base_units, if they haven't been given yet
    for key, value in quantity_magnitude.to_json().items():
        if key not in instance:
            instance[key] = value

    if not isinstance(instance['dimensionality'], str):
        raise ValidationError('dimensionality must be str', path)
    if quantity_magnitude.dimensionality != schema_quantity.dimensionality:
        raise ValidationError(f'Invalid units, expected units for dimensionality "{str(schema_quantity.dimensionality)}"', path)
    if str(quantity_magnitude.dimensionality) != instance['dimensionality']:
        raise ValidationError(f'Invalid dimensionality, expected "{str(schema_quantity.dimensionality)}"', path)


def _validate_sample(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validates the given instance using the given sample object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'object_id'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'sample':
        raise ValidationError('expected _type "sample"', path)
    if not isinstance(instance['object_id'], int):
        raise ValidationError('object_id must be int', path)
    if 'component_uuid' in instance and instance['component_uuid'] != flask.current_app.config['FEDERATION_UUID']:
        pass
    elif 'eln_source_url' in instance:
        validate_eln_urls(instance, path)
    else:
        try:
            sample = objects.get_object(object_id=instance['object_id'])
        except ObjectDoesNotExistError:
            raise ValidationError('object does not exist', path)
        if sample.action_id is None:
            raise ValidationError('object must be sample', path)
        action = actions.get_action(sample.action_id)
        if action.type is None:
            raise ValidationError('object must be sample', path)
        if ActionType.SAMPLE_CREATION not in {action.type_id, action.type.fed_id}:
            raise ValidationError('object must be sample', path)


def _validate_measurement(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validates the given instance using the given measurement object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'object_id'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'measurement':
        raise ValidationError('expected _type "measurement"', path)
    if not isinstance(instance['object_id'], int):
        raise ValidationError('object_id must be int', path)
    if 'component_uuid' in instance and instance['component_uuid'] != flask.current_app.config['FEDERATION_UUID']:
        pass
    elif 'eln_source_url' in instance:
        validate_eln_urls(instance, path)
    else:
        try:
            measurement = objects.get_object(object_id=instance['object_id'])
        except ObjectDoesNotExistError:
            raise ValidationError('object does not exist', path)
        if measurement.action_id is None:
            raise ValidationError('object must be measurement', path)
        action = actions.get_action(measurement.action_id)
        if action.type is None:
            raise ValidationError('object must be measurement', path)
        if ActionType.MEASUREMENT not in {action.type_id, action.type.fed_id}:
            raise ValidationError('object must be measurement', path)


def _validate_user(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validates the given instance using the given user object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'user_id'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'user':
        raise ValidationError('expected _type "user"', path)
    if not isinstance(instance['user_id'], int):
        raise ValidationError('user_id must be int', path)
    if instance['user_id'] < 1:
        raise ValidationError('user_id must be positive', path)
    if 'component_uuid' in instance and instance['component_uuid'] != flask.current_app.config['FEDERATION_UUID']:
        pass  # TODO
    elif 'eln_source_url' in instance:
        validate_eln_urls(instance, path)
    else:
        try:
            users.check_user_exists(user_id=instance['user_id'])
        except UserDoesNotExistError:
            raise ValidationError('user does not exist', path)


def _validate_object_reference(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validates the given instance using the given object reference object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'object_id'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'object_reference':
        raise ValidationError('expected _type "object_reference"', path)
    if not isinstance(instance['object_id'], int):
        raise ValidationError('object_id must be int', path)
    if instance['object_id'] < 1:
        raise ValidationError('object_id must be positive', path)
    if 'component_uuid' in instance and instance['component_uuid'] != flask.current_app.config['FEDERATION_UUID']:
        pass
    elif 'eln_source_url' in instance:
        validate_eln_urls(instance, path)
    else:
        try:
            object = objects.get_object(object_id=instance['object_id'])
        except ObjectDoesNotExistError:
            raise ValidationError('object does not exist', path)
        filter_operator = schema.get('filter_operator', 'and')
        action_id_error = None
        if 'action_id' in schema:
            if type(schema['action_id']) is int:
                valid_action_ids = [schema['action_id']]
            else:
                valid_action_ids = schema['action_id']
            if valid_action_ids is not None:
                if object.action_id is None:
                    action_id_error = 'object has no action'
                elif object.action_id not in valid_action_ids:
                    action_id_error = 'object has wrong action'
        if filter_operator == 'and' and action_id_error:
            raise ValidationError(action_id_error, path)
        action_type_id_error = None
        if 'action_type_id' in schema:
            if type(schema['action_type_id']) is int:
                valid_action_type_ids = [schema['action_type_id']]
            else:
                valid_action_type_ids = schema['action_type_id']
            if valid_action_type_ids is not None:
                if object.action_id is None:
                    action_type_id_error = 'object has no action type'
                else:
                    action = actions.get_action(object.action_id)
                    if action.type is None:
                        action_type_id_error = 'object has no action type'
                    elif action.type_id not in valid_action_type_ids and (action.type.fed_id is None or action.type.fed_id >= 0 or action.type.fed_id not in valid_action_type_ids):
                        action_type_id_error = 'object has wrong action type'
        if filter_operator == 'and' and action_type_id_error:
            raise ValidationError(action_type_id_error, path)
        if filter_operator == 'or' and action_id_error and action_type_id_error:
            raise ValidationError(action_id_error, path)


def _validate_plotly_chart(instance: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Validates the given instance using the given text object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'plotly'}
    required_keys = ['_type', 'plotly']
    schema_keys = instance.keys()
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'plotly_chart':
        raise ValidationError('expected _type "plotly_chart"', path)
    if isinstance(instance['plotly'], str):
        if len(instance['plotly']) > 0:
            try:
                instance['plotly'] = json.loads(instance['plotly'])
            except json.JSONDecodeError:
                raise ValidationError(_('plotly data must be valid JSON'), path)
        else:
            instance['plotly'] = {}
    if not isinstance(instance['plotly'], dict):
        raise ValidationError(_('plotly must be a dict'), path)

    try:
        plotly.io.from_json(json.dumps(instance['plotly']), 'Figure', False)
    except ValueError:
        raise ValidationError(_('The plotly data must be valid. Look up which schema is supported by plotly.'), path)


def _validate_timeseries(
        instance: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str]
) -> None:
    """
    Validates the given instance using the given timeseries schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    required_keys = {'_type', 'data'}
    valid_keys = required_keys.union({'units', 'dimensionality', 'data'})
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'timeseries':
        raise ValidationError('expected _type "timeseries"', path)
    if 'units' not in instance:
        instance['units'] = schema['units']
    if not isinstance(instance['units'], str):
        raise ValidationError('units must be str', path)
    if not units_are_valid(instance['units']):
        raise ValidationError('Invalid/Unknown units', path)
    try:
        if isinstance(schema['units'], str):
            schema_units = schema['units']
        else:
            schema_units = schema['units'][0]
        dimensionality_from_schema_units = get_dimensionality_for_units(schema_units)
    except Exception:
        raise ValidationError('Unable to determine dimensionality', path)
    if isinstance(schema['units'], str) and instance['units'] != schema['units']:
        if dimensionality_from_schema_units != get_dimensionality_for_units(instance['units']):
            raise ValidationError(f'Invalid units, expected {schema["units"]}', path)
    if isinstance(schema['units'], list) and instance['units'] not in schema['units']:
        if dimensionality_from_schema_units != get_dimensionality_for_units(instance['units']):
            raise ValidationError(f'Invalid units, expected one of {", ".join(schema["units"])}', path)
    if 'dimensionality' in instance:
        if not isinstance(instance['dimensionality'], str):
            raise ValidationError('dimensionality must be str', path)
        if instance['dimensionality'] != dimensionality_from_schema_units:
            raise ValidationError('dimensionality must match units', path)
    else:
        instance['dimensionality'] = dimensionality_from_schema_units

    if not isinstance(instance['data'], list):
        raise ValidationError('data must be list', path)

    is_relative_time = len(instance['data']) > 0 and len(instance['data'][0]) > 0 and type(instance['data'][0][0]) in (int, float)
    if (
        (not is_relative_time and not all(isinstance(entry, (list, tuple)) and len(entry) in (2, 3) and type(entry[0]) is str and all(type(value) in (int, float) for value in entry[1:]) for entry in instance['data'])) or
        (is_relative_time and not all(isinstance(entry, (list, tuple)) and len(entry) in (2, 3) and type(entry[0]) in (int, float) and all(type(value) in (int, float) for value in entry[1:]) for entry in instance['data']))
    ):
        raise ValidationError('data must be list of lists containing either a datetime string or relative time in seconds, and 1 or 2 numbers', path)

    existing_times = set()
    for i, entry in enumerate(instance['data']):
        time, magnitude = entry[:2]
        if not math.isfinite(magnitude):
            raise ValidationError('magnitude must be finite', path)
        if time in existing_times:
            raise ValidationError('duplicate point in timeseries', path)
        if not is_relative_time:
            try:
                datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')
            except Exception:
                raise ValidationError('invalid datetime in timeseries, expected format: YYYY-MM-DD hh:mm:ss.ffffff', path)
        elif not math.isfinite(time):
            raise ValidationError('relative time must be finite', path)
        existing_times.add(time)
        calculated_magnitude_in_base_units = get_magnitude_in_base_units(magnitude=decimal.Decimal(magnitude), units=instance['units'])
        if len(entry) == 3:
            magnitude_in_base_units = entry[2]
            if not math.isfinite(magnitude_in_base_units):
                raise ValidationError('magnitude_in_base_units must be finite', path)
            if not math.isclose(float(calculated_magnitude_in_base_units), magnitude_in_base_units):
                raise ValidationError('magnitude_in_base_units and magnitude do not match', path)
        else:
            instance['data'][i] = [time, float(magnitude), float(calculated_magnitude_in_base_units)]


def _validate_file(
        instance: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        file_names_by_id: typing.Optional[typing.Dict[int, str]] = None
) -> None:
    """
    Validates the given instance using the given file object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb file object
    :param schema: the valid sampledb file object schema
    :param path: the path to this subinstance / subschema
    :param file_names_by_id: a dict mapping file IDs to file names, or None
    :raise ValidationError: if the schema is invalid
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'file_id'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys - OPT_IMPORT_KEYS
    if invalid_keys:
        raise ValidationError(f'unexpected keys in schema: {invalid_keys}', path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError(f'missing keys in schema: {missing_keys}', path)
    if instance['_type'] != 'file':
        raise ValidationError('expected _type "file"', path)
    if not isinstance(instance['file_id'], int):
        raise ValidationError('file_id must be int', path)
    if file_names_by_id is not None:
        if instance['file_id'] not in file_names_by_id:
            raise ValidationError('file does not exist', path)
        file_name = file_names_by_id[instance['file_id']]
        if 'extensions' in schema:
            for extension in schema['extensions']:
                if file_name.lower().endswith(extension.lower()):
                    break
            else:
                raise ValidationError(f'file name should have one of these extensions: {", ".join(schema["extensions"])}', path)


def validate_eln_urls(
        instance: typing.Dict[str, typing.Any],
        path: typing.List[str]
) -> None:
    for key in ['eln_source_url', 'eln_user_url', 'eln_object_url']:
        if instance.get(key) is not None:
            try:
                parse_url(instance[key], valid_schemes=('http', 'https'))
            except InvalidURLError:
                raise ValidationError(f'{key} must be a valid http oder https URL', path)
