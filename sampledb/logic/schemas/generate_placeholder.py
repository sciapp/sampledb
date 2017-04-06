# coding: utf-8
"""

"""

import typing
from .errors import SchemaError
from .utils import units_are_valid, get_dimensionality_for_units


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'



def generate_placeholder(schema: dict, path: typing.Union[None, typing.List[str]]=None) -> typing.Union[dict, list, None]:
    """
    Generates a placeholder object based on an object schema.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default
    """
    if path is None:
        path = []
    if 'type' not in schema:
        raise SchemaError('invalid schema', path)
    if schema['type'] == 'array':
        return _generate_array_placeholder(schema, path)
    elif schema['type'] == 'object':
        return _generate_object_placeholder(schema, path)
    elif schema['type'] == 'text':
        return _generate_text_placeholder(schema, path)
    elif schema['type'] == 'datetime':
        return _generate_datetime_placeholder(schema, path)
    elif schema['type'] == 'bool':
        return _generate_bool_placeholder(schema, path)
    elif schema['type'] == 'quantity':
        return _generate_quantity_placeholder(schema, path)
    else:
        raise SchemaError('invalid type', path)


def _generate_array_placeholder(schema: dict, path: typing.List[str]) -> list:
    """
    Generates a placeholder array object based on an object schema.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object
    """
    if 'default' in schema:
        return schema['default']
    if 'minItems' not in schema:
        return []
    min_items = schema['minItems']
    item_schema = schema['items']
    return [
        generate_placeholder(item_schema, path + ['[?]'])
        for _ in range(min_items)
    ]


def _generate_object_placeholder(schema: dict, path: typing.List[str]) -> dict:
    """
    Generates a placeholder object based on an object schema.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object
    """
    if 'default' in schema:
        return schema['default']
    properties = schema['properties']
    return {
        property_name: generate_placeholder(property_schema, path + [property_name])
        for property_name, property_schema in properties.items()
    }


def _generate_bool_placeholder(schema: dict, path: typing.List[str]) -> typing.Union[dict, None]:
    """
    Generates a placeholder boolean object based on an object schema.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default value
    """
    if 'default' not in schema:
        return None
    value = schema['default']
    return {
        '_type': 'bool',
        'value': value
    }


def _generate_text_placeholder(schema: dict, path: typing.List[str]) -> typing.Union[dict, None]:
    """
    Generates a placeholder text object based on an object schema.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default text
    """
    if 'default' not in schema:
        return None
    text = schema['default']
    return {
        '_type': 'text',
        'text': text
    }


def _generate_datetime_placeholder(schema: dict, path: typing.List[str]) -> typing.Union[dict, None]:
    """
    Generates a placeholder datetime object based on an object schema.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default datetime
    """
    if 'default' not in schema:
        return None
    utc_datetime = schema['default']
    return {
        '_type': 'datetime',
        'utc_datetime': utc_datetime
    }


def _generate_quantity_placeholder(schema: dict, path: typing.List[str]) -> typing.Union[dict, None]:
    """
    Generates a placeholder quantity object based on an object schema.
    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default magnitude (in base units)
    """
    if 'default' not in schema:
        return None
    magnitude_in_base_units = schema['default']
    units = schema['units']

    if not units_are_valid(units):
        raise SchemaError('invalid units', path)
    dimensionality = get_dimensionality_for_units(units)
    return {
        '_type': 'quantity',
        'dimensionality': dimensionality,
        'units': units,
        'magnitude_in_base_units': magnitude_in_base_units
    }