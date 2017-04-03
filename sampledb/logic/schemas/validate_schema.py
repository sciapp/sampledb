# coding: utf-8
"""

"""


import datetime
import typing

from .errors import ValidationError
from .utils import units_are_valid
from .validate import validate

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def validate_schema(schema: dict, path: typing.Union[None, typing.List[str]]=None) -> None:
    """
    Validates the given schema and raises a ValidationError if it is invalid.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raises: ValidationError, if the schema is invalid.
    """
    if path is None:
        path = []
    if not isinstance(schema, dict):
        raise ValidationError('invalid schema (must be dict)', path)
    if 'type' not in schema:
        raise ValidationError('invalid schema (must contain type)', path)
    if not isinstance(schema['type'], str):
        raise ValidationError('invalid schema (type must be str)', path)
    if 'title' not in schema:
        raise ValidationError('invalid schema (must contain title)', path)
    if not isinstance(schema['title'], str):
        raise ValidationError('invalid schema (title must be str)', path)
    if schema['type'] == 'array':
        return _validate_array_schema(schema, path)
    elif schema['type'] == 'object':
        return _validate_object_schema(schema, path)
    elif schema['type'] == 'text':
        return _validate_text_schema(schema, path)
    elif schema['type'] == 'datetime':
        return _validate_datetime_schema(schema, path)
    elif schema['type'] == 'bool':
        return _validate_bool_schema(schema, path)
    elif schema['type'] == 'quantity':
        return _validate_quantity_schema(schema, path)
    else:
        raise ValidationError('invalid type', path)


def _validate_array_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given array schema and raises a ValidationError if it is invalid.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raises: ValidationError, if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'items', 'style', 'minItems', 'maxItems', 'default'}
    required_keys = {'type', 'title', 'items'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    has_min_items = False
    if 'minItems' in schema:
        if not isinstance(schema['minItems'], int):
            raise ValidationError('minItems must be an integer', path)
        elif schema['minItems'] < 0:
            raise ValidationError('minItems must not be negative', path)
        else:
            has_min_items = True
    has_max_items = True
    if 'maxItems' in schema:
        if not isinstance(schema['maxItems'], int):
            raise ValidationError('maxItems must be an integer', path)
        elif schema['maxItems'] < 0:
            raise ValidationError('maxItems must not be negative', path)
        else:
            has_max_items = True
    if has_min_items and has_max_items:
        if schema['minItems'] > schema['maxItems']:
            raise ValidationError('minItems must not be less than or equal to maxItems', path)
    if 'style' in schema and schema['style'] not in ('table', 'list'):
        raise ValidationError('style must be either "list" or "table"', path)
    validate_schema(schema['items'], path + ['[?]'])
    if 'default' in schema:
        validate(schema['default'], schema, path + ['(default)'])


def _validate_object_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given object schema and raises a ValidationError if it is invalid.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raises: ValidationError, if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'properties', 'propertyOrder', 'required', 'default'}
    required_keys = {'type', 'title', 'properties'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if not isinstance(schema['properties'], dict):
        raise ValidationError('properties must be dict', path)
    for property_name, property_schema in schema['properties'].items():
        validate_schema(property_schema, path + [property_name])

    if 'required' in schema:
        if not isinstance(schema['required'], list):
            raise ValidationError('required must be list', path)
        for property_name in schema['required']:
            if property_name not in schema['properties']:
                raise ValidationError('unknown required property: {}'.format(property_name), path)

    if 'propertyOrder' in schema:
        if not isinstance(schema['propertyOrder'], list):
            raise ValidationError('propertyOrder must be list', path)
        for property_name in schema['propertyOrder']:
            if property_name not in schema['properties']:
                raise ValidationError('unknown propertyOrder property: {}'.format(property_name), path)

    if 'default' in schema:
        validate(schema['default'], schema)


def _validate_text_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given text object schema and raises a ValidationError if it is invalid.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raises: ValidationError, if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'default' in schema and not isinstance(schema['default'], str):
        raise ValidationError('default must be str', path)


def _validate_datetime_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given datetime object schema and raises a ValidationError if it is invalid.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raises: ValidationError, if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'default' in schema:
        if not isinstance(schema['default'], str):
            raise ValidationError('default must be str', path)
        else:
            try:
                datetime.datetime.strptime(schema['default'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise ValidationError('invalid default value', path)


def _validate_bool_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given boolean object schema and raises a ValidationError if it is invalid.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raises: ValidationError, if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'default' in schema and not isinstance(schema['default'], bool):
        raise ValidationError('default must be bool', path)


def _validate_quantity_schema(schema: dict, path: typing.List[str]) -> None:
    """
    Validates the given quantity object schema and raises a ValidationError if it is invalid.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raises: ValidationError, if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'units', 'default'}
    required_keys = {'type', 'title', 'units'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if not isinstance(schema['units'], str):
        raise ValidationError('units must be str', path)
    elif not units_are_valid(schema['units']):
        raise ValidationError('invalid units', path)

    if 'default' in schema and not isinstance(schema['default'], float) and not isinstance(schema['default'], int):
        raise ValidationError('default must be float or int', path)
