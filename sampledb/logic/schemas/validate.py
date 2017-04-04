# coding: utf-8
"""

"""

import datetime
import typing

from .errors import ValidationError, ValidationMultiError

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def validate(instance: typing.Union[dict, list], schema: dict, path: typing.Union[None, typing.List[str]]=None) -> None:
    """
    Validates the given instance using the given schema and raises a ValidationError if it is invalid.
    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raises: ValidationError, if the schema is invalid.
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
    else:
        raise ValidationError('invalid type', path)


def _validate_array(instance: list, schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given instance using the given array schema and raises a ValidationError if it is invalid.
    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raises: ValidationError, if the schema is invalid.
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


def _validate_object(instance: dict, schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given instance using the given object schema and raises a ValidationError if it is invalid.
    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raises: ValidationError, if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    errors = []
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
    :raises: ValidationError, if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'text'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'text':
        raise ValidationError('expected _type "text"', path)
    if not isinstance(instance['text'], str):
        raise ValidationError('text must be str', path)


def _validate_datetime(instance: dict, schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given instance using the given datetime object schema and raises a ValidationError if it is invalid.
    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raises: ValidationError, if the schema is invalid.
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
        raise ValidationError('invalid utc_datetime', path)


def _validate_bool(instance: dict, schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given instance using the given boolean object schema and raises a ValidationError if it is invalid.
    :param instance: the sampledb object
    :param schema: the valid sampledb object schema
    :param path: the path to this subinstance / subschema
    :raises: ValidationError, if the schema is invalid.
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
    :raises: ValidationError, if the schema is invalid.
    """
    if not isinstance(instance, dict):
        raise ValidationError('instance must be dict', path)
    valid_keys = {'_type', 'units', 'dimensionality', 'magnitude_in_base_units'}
    required_keys = valid_keys
    schema_keys = set(instance.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if instance['_type'] != 'quantity':
        raise ValidationError('expected _type "quantity"', path)
    if not isinstance(instance['units'], str):
        raise ValidationError('units must be str', path)
    if not isinstance(instance['dimensionality'], str):
        raise ValidationError('dimensionality must be str', path)
    if not isinstance(instance['magnitude_in_base_units'], float) and not isinstance(instance['magnitude_in_base_units'], int):
        raise ValidationError('magnitude_in_base_units must be float or int', path)
