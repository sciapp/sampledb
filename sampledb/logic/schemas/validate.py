# coding: utf-8
"""
Implementation of validate(instance, schema)
"""

import re
import datetime
import typing
import math
import json

import plotly
from flask_babel import _

from .conditions import are_conditions_fulfilled
from ...logic import actions, objects, datatypes, users, languages
from ...models import ActionType
from ..errors import ObjectDoesNotExistError, ValidationError, ValidationMultiError, UserDoesNotExistError
from .utils import units_are_valid
from ..utils import get_translated_text


def validate(
        instance: typing.Union[dict, list],
        schema: dict,
        path: typing.Optional[typing.List[str]] = None
) -> None:
    """
    Validates the given instance using the given schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if path is None:
        path = []
    if not isinstance(schema, dict):
        raise ValidationError('invalid schema (must be dict)', path)
    if 'type' not in schema:
        raise ValidationError('invalid schema (must contain type)', path)
    if schema['type'] == 'array':
        return _validate_array(instance, schema, path)
    elif schema['type'] == 'object':
        return _validate_object(instance, schema, path)
    elif schema['type'] == 'text':
        return _validate_text(instance, schema, path)
    elif schema['type'] == 'datetime':
        return _validate_datetime(instance, schema, path)
    elif schema['type'] == 'bool':
        return _validate_bool(instance, schema, path)
    elif schema['type'] == 'quantity':
        return _validate_quantity(instance, schema, path)
    elif schema['type'] == 'sample':
        return _validate_sample(instance, schema, path)
    elif schema['type'] == 'measurement':
        return _validate_measurement(instance, schema, path)
    elif schema['type'] == 'object_reference':
        return _validate_object_reference(instance, schema, path)
    elif schema['type'] == 'tags':
        return _validate_tags(instance, schema, path)
    elif schema['type'] == 'hazards':
        return _validate_hazards(instance, schema, path)
    elif schema['type'] == 'user':
        return _validate_user(instance, schema, path)
    elif schema['type'] == 'plotly_chart':
        return _validate_plotly_chart(instance, schema, path)
    else:
        raise ValidationError('invalid type', path)


def _validate_array(instance: list, schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given instance using the given array schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, list):
        raise ValidationError('instance must be list', path)
    if 'minItems' in schema and len(instance) < schema['minItems']:
        raise ValidationError('expected at least {} items'.format(schema['minItems']), path)
    if 'maxItems' in schema and len(instance) > schema['maxItems']:
        raise ValidationError('expected at most {} items'.format(schema['maxItems']), path)
    errors = []
    for index, item in enumerate(instance):
        try:
            validate(item, schema['items'], path + [str(index)])
        except ValidationError as e:
            errors.append(e)
    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        raise ValidationMultiError(errors)


def _validate_hazards(instance: list, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'hazards':
        raise ValidationError('expected _type "hazards"', path)
    if not isinstance(instance['hazards'], list):
        raise ValidationError('hazards must be list', path)
    errors = []
    hazards = []
    for index, item in enumerate(instance['hazards']):
        if not isinstance(item, int):
            errors.append(ValidationError('invalid hazard index type: {}'.format(type(item)), path + ['hazards', str(index)]))
        elif item in hazards:
            errors.append(ValidationError('duplicate hazard index: {}'.format(item), path + ['hazards', str(index)]))
        elif item < 1 or item > 9:
            errors.append(ValidationError('invalid hazard index: {}'.format(item), path + ['hazards', str(index)]))
        else:
            hazards.append(item)

    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        raise ValidationMultiError(errors)


def _validate_tags(instance: list, schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given instance using the given tags schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'tags'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'tags':
        raise ValidationError('expected _type "tags"', path)
    if not isinstance(instance['tags'], list):
        raise ValidationError('tags must be list', path)
    errors = []
    tags = []
    for index, item in enumerate(instance['tags']):
        if not isinstance(item, str):
            errors.append(ValidationError('invalid tag type: {}'.format(type(item)), path + ['tags', str(index)]))
        elif item in tags:
            errors.append(ValidationError('duplicate tag: {}'.format(item), path + ['tags', str(index)]))
        elif item.lower() != item:
            errors.append(ValidationError('tag not lowercase: {}'.format(item), path + ['tags', str(index)]))
        elif any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-äöüß' for c in item):
            errors.append(ValidationError('tag contains invalid character: {}'.format(item), path + ['tags', str(index)]))
        else:
            tags.append(item)

    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        raise ValidationMultiError(errors)


def _validate_object(instance: dict, schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given instance using the given object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    errors = []

    for property_name, property_schema in schema['properties'].items():
        if property_name not in instance:
            continue
        if not are_conditions_fulfilled(property_schema.get('conditions'), instance):
            errors.append(ValidationError('conditions for property "{}" not fulfilled'.format(property_name), path + [property_name]))

    if 'required' in schema:
        for property_name in schema['required']:
            if property_name not in instance:
                errors.append(ValidationError('missing required property "{}"'.format(property_name), path + [property_name]))
    for property_name, property_value in instance.items():
        try:
            if property_name not in schema['properties']:
                raise ValidationError('unknown property "{}"'.format(property_name), path + [property_name])
            else:
                validate(property_value, schema['properties'][property_name], path + [property_name])
        except ValidationError as e:
            errors.append(e)
    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        raise ValidationMultiError(errors)


def _validate_text(instance: dict, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'text':
        raise ValidationError('expected _type "text"', path)
    if not isinstance(instance['text'], str) and not isinstance(instance['text'], dict):
        raise ValidationError('text must be str or a dictionary', path)
    choices = schema.get('choices', None)
    if choices and instance['text'] not in choices:
        raise ValidationError(_('The text must be one of %(choices)s.', choices=choices), path)
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
                    if language.enabled_for_input
                }
            else:
                allowed_language_codes = {
                    language.lang_code
                    for language in all_languages
                    if language.enabled_for_input and language.lang_code in schema['languages']
                }
        else:
            allowed_language_codes = {'en'}
        for text in instance['text'].values():
            if len(text) < min_length:
                raise ValidationError(_('The text must be at least %(min_length)s characters long.', min_length=min_length), path)
            if max_length is not None and len(text) > max_length:
                raise ValidationError(_('The text must be at most %(max_length)s characters long.', max_length=max_length), path)
        for lang in instance['text'].keys():
            if lang not in allowed_language_codes:
                raise ValidationError(_('The language "%(lang_code)s" is not allowed for this field.', lang_code=language_names.get(lang, lang)), path)
    if 'pattern' in schema:
        if isinstance(instance['text'], dict):
            for text in instance['text'].values():
                if re.match(schema['pattern'], text) is None:
                    raise ValidationError(_('Input must match: %(pattern)s', pattern=schema['pattern']), path)
        else:
            if re.match(schema['pattern'], instance['text']) is None:
                raise ValidationError(_('Input must match: %(pattern)s', pattern=schema['pattern']), path)
    if 'is_markdown' in instance and not isinstance(instance['is_markdown'], bool):
        raise ValidationError('is_markdown must be bool', path)


def _validate_datetime(instance: dict, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'datetime':
        raise ValidationError('expected _type "datetime"', path)
    if not isinstance(instance['utc_datetime'], str):
        raise ValidationError('utc_datetime must be str', path)
    try:
        datetime.datetime.strptime(instance['utc_datetime'], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise ValidationError(_('Please enter the date and time in the format: %(datetime_format)s', datetime_format='YYYY-MM-DD HH:MM:SS'), path)


def _validate_bool(instance: dict, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'bool':
        raise ValidationError('expected _type "bool"', path)
    if not isinstance(instance['value'], bool):
        raise ValidationError('value must be bool', path)


def _validate_quantity(instance: dict, schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given instance using the given quantity object schema and raises a ValidationError if it is invalid.

    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raise ValidationError: if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'units', 'dimensionality', 'magnitude_in_base_units', 'magnitude'}
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    if instance['_type'] != 'quantity':
        raise ValidationError('expected _type "quantity"', path)
    if 'units' not in instance:
        instance['units'] = schema['units']
    if not isinstance(instance['units'], str):
        raise ValidationError('units must be str', path)
    if not units_are_valid(instance['units']):
        raise ValidationError('Invalid/Unknown units', path)
    try:
        schema_quantity = datatypes.Quantity(1.0, units=schema['units'])
    except Exception:
        raise ValidationError('Unable to create schema quantity', path)

    quantity_magnitude = None
    quantity_magnitude_in_base_units = None

    if 'magnitude' in instance:
        if not isinstance(instance['magnitude'], float) and not isinstance(instance['magnitude'], int):
            raise ValidationError('magnitude must be float or int', path)
        try:
            quantity_magnitude = datatypes.Quantity(instance['magnitude'], units=instance['units'],
                                                    already_in_base_units=False)
        except Exception:
            raise ValidationError('Unable to create quantity based on given magnitude', path)
    if 'magnitude_in_base_units' in instance:
        if not isinstance(instance['magnitude_in_base_units'], float) and not isinstance(instance['magnitude_in_base_units'], int):
            raise ValidationError('magnitude_in_base_units must be float or int', path)
        try:
            quantity_magnitude_in_base_units = datatypes.Quantity(instance['magnitude_in_base_units'], units=instance['units'],
                                                                  already_in_base_units=True)
        except Exception:
            raise ValidationError('Unable to create quantity based on given magnitude_in_base_units', path)

    if quantity_magnitude is not None and quantity_magnitude_in_base_units is not None \
            and not math.isclose(quantity_magnitude.magnitude, quantity_magnitude_in_base_units.magnitude):
        raise ValidationError(
            'magnitude and magnitude_in_base_units do not match, either set only one or make sure both match', path)
    elif quantity_magnitude is None and quantity_magnitude_in_base_units is None:
        raise ValidationError(
            'missing keys in schema: either magnitude or magnitude_in_base_units has to be given', None)
    elif quantity_magnitude is None:
        quantity_magnitude = quantity_magnitude_in_base_units

    # automatically add dimensionality and either magnitude oder magnitude_in_base_units, if they haven't been given yet
    for key, value in quantity_magnitude.to_json().items():
        if key not in instance:
            instance[key] = value

    if not isinstance(instance['dimensionality'], str):
        raise ValidationError('dimensionality must be str', path)
    if quantity_magnitude.dimensionality != schema_quantity.dimensionality:
        raise ValidationError('Invalid units, expected units for dimensionality "{}"'.format(str(schema_quantity.dimensionality)), path)
    if str(quantity_magnitude.dimensionality) != instance['dimensionality']:
        raise ValidationError('Invalid dimensionality, expected "{}"'.format(str(schema_quantity.dimensionality)), path)


def _validate_sample(instance: dict, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'sample':
        raise ValidationError('expected _type "sample"', path)
    if not isinstance(instance['object_id'], int):
        raise ValidationError('object_id must be int', path)
    try:
        sample = objects.get_object(object_id=instance['object_id'])
    except ObjectDoesNotExistError:
        raise ValidationError('object does not exist', path)
    action = actions.get_action(sample.action_id)
    if action.type_id != ActionType.SAMPLE_CREATION:
        raise ValidationError('object must be sample', path)


def _validate_measurement(instance: dict, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'measurement':
        raise ValidationError('expected _type "measurement"', path)
    if not isinstance(instance['object_id'], int):
        raise ValidationError('object_id must be int', path)
    try:
        measurement = objects.get_object(object_id=instance['object_id'])
    except ObjectDoesNotExistError:
        raise ValidationError('object does not exist', path)
    action = actions.get_action(measurement.action_id)
    if action.type_id != ActionType.MEASUREMENT:
        raise ValidationError('object must be measurement', path)


def _validate_user(instance: dict, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'user':
        raise ValidationError('expected _type "user"', path)
    if not isinstance(instance['user_id'], int):
        raise ValidationError('user_id must be int', path)
    try:
        users.get_user(user_id=instance['user_id'])
    except UserDoesNotExistError:
        raise ValidationError('user does not exist', path)


def _validate_object_reference(instance: dict, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'object_reference':
        raise ValidationError('expected _type "object_reference"', path)
    if not isinstance(instance['object_id'], int):
        raise ValidationError('object_id must be int', path)
    try:
        object = objects.get_object(object_id=instance['object_id'])
    except ObjectDoesNotExistError:
        raise ValidationError('object does not exist', path)
    if 'action_id' in schema and isinstance(schema['action_id'], int) and object.action_id != schema['action_id']:
        raise ValidationError('object has wrong action', path)
    if 'action_type_id' in schema and isinstance(schema['action_type_id'], int):
        action = actions.get_action(object.action_id)
        if action.type_id != schema['action_type_id']:
            raise ValidationError('object has wrong action type', path)


def _validate_plotly_chart(instance: dict, schema: dict, path: typing.List[str]) -> None:
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
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
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
