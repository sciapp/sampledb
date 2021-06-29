# coding: utf-8
"""
Implementation of generate_placeholder(schema)
"""

import typing

from ..errors import UndefinedUnitError, SchemaError
from .utils import get_dimensionality_for_units


def generate_placeholder(schema: dict, path: typing.Optional[typing.List[str]] = None) -> typing.Union[dict, list, None]:
    """
    Generates a placeholder object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default
    :raise SchemaError: if the type is missing or invalid, or if the schema
        contains a quantity with invalid units
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
    elif schema['type'] == 'sample':
        return _generate_sample_placeholder(schema, path)
    elif schema['type'] == 'measurement':
        return _generate_measurement_placeholder(schema, path)
    elif schema['type'] == 'object_reference':
        return _generate_object_reference_placeholder(schema, path)
    elif schema['type'] == 'tags':
        return _generate_tags_placeholder(schema, path)
    elif schema['type'] == 'hazards':
        return _generate_hazards_placeholder(schema, path)
    elif schema['type'] == 'user':
        return _generate_user_placeholder(schema, path)
    elif schema['type'] == 'plotly_chart':
        return _generate_plotly_chart_placeholder(schema, path)
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
    item_schema = schema['items']
    default_items = schema.get('defaultItems', schema.get('minItems', 0))
    return [
        generate_placeholder(item_schema, path + ['[?]'])
        for _ in range(default_items)
    ]


def _generate_tags_placeholder(schema: dict, path: typing.List[str]) -> dict:
    """
    Generates a placeholder tags object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object
    """
    if 'default' in schema:
        return {
            '_type': 'tags',
            'tags': schema['default']
        }
    return {
        '_type': 'tags',
        'tags': []
    }


def _generate_hazards_placeholder(schema: dict, path: typing.List[str]) -> dict:
    """
    Generate a placeholder GHS hazards object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object
    """
    return {
        '_type': 'hazards'
    }


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
    :raise SchemaError: if the units are invalid
    """
    if 'default' not in schema:
        return None
    magnitude_in_base_units = schema['default']
    units = schema['units']

    try:
        dimensionality = get_dimensionality_for_units(units)
    except UndefinedUnitError:
        raise SchemaError('invalid units', path)
    return {
        '_type': 'quantity',
        'dimensionality': dimensionality,
        'units': units,
        'magnitude_in_base_units': magnitude_in_base_units
    }


def _generate_sample_placeholder(schema: dict, path: typing.List[str]) -> None:
    """
    Generates a placeholder sample object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there can be no default sample
    """
    return _generate_object_reference_placeholder(schema, path)


def _generate_measurement_placeholder(schema: dict, path: typing.List[str]) -> None:
    """
    Generates a placeholder measurement object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there can be no default measurement
    """
    return _generate_object_reference_placeholder(schema, path)


def _generate_object_reference_placeholder(schema: dict, path: typing.List[str]) -> None:
    """
    Generates a placeholder object reference object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there can be no default object reference
    """
    return None


def _generate_user_placeholder(schema: dict, path: typing.List[str]) -> None:
    """
    Generates a placeholder user object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there can be no default user
    """
    return None


def _generate_plotly_chart_placeholder(schema: dict, path: typing.List[str]) -> typing.Union[dict, None]:
    """
    Generates a placeholder plotly_chart object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default text
    """
    return None
