# coding: utf-8
"""
Implementation of generate_placeholder(schema)
"""
import copy
import typing

from flask_login import current_user

from ..errors import UndefinedUnitError, SchemaError, UserDoesNotExistError
from ..schemas.validate import validate
from .utils import get_dimensionality_for_units
from ..users import check_user_exists


def get_default_data(
        schema: typing.Dict[str, typing.Any],
        property_path: typing.Tuple[typing.Union[str, int], ...]
) -> typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]]:
    """
    Return the default data for given schema and property path.

    :param schema: the sampledb object schema
    :param property_path: the path in the schema to generate a value for
    :return: the default data at the given path or None, if there is no default for that path
    """
    current_default_data = generate_placeholder(schema)
    has_default_value = current_default_data is not None
    current_schema: typing.Dict[str, typing.Any] = schema
    for path_element in property_path:
        if current_schema['type'] == 'array':
            current_schema = current_schema.get('items', {})
        else:
            current_schema = current_schema.get('properties', {}).get(path_element)
        if not current_schema:
            return None
        if has_default_value:
            if isinstance(current_default_data, dict) and isinstance(path_element, str):
                current_default_data = current_default_data.get(path_element)
            elif isinstance(current_default_data, list) and isinstance(path_element, int) and 0 <= path_element < len(current_default_data):
                current_default_data = current_default_data[path_element]
            else:
                current_default_data = None
                has_default_value = False
        if not has_default_value:
            current_default_data = generate_placeholder(current_schema)
            has_default_value = current_default_data is not None
    return current_default_data


def generate_placeholder(
        schema: typing.Dict[str, typing.Any],
        path: typing.Optional[typing.List[str]] = None
) -> typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]]:
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
        return _generate_sample_placeholder(schema, path)  # type: ignore
    elif schema['type'] == 'measurement':
        return _generate_measurement_placeholder(schema, path)  # type: ignore
    elif schema['type'] == 'object_reference':
        return _generate_object_reference_placeholder(schema, path)  # type: ignore
    elif schema['type'] == 'tags':
        return _generate_tags_placeholder(schema, path)
    elif schema['type'] == 'hazards':
        return _generate_hazards_placeholder(schema, path)
    elif schema['type'] == 'user':
        return _generate_user_placeholder(schema, path)
    elif schema['type'] == 'plotly_chart':
        return _generate_plotly_chart_placeholder(schema, path)
    elif schema['type'] == 'timeseries':
        return _generate_timeseries_placeholder(schema, path)
    elif schema['type'] == 'file':
        return _generate_file_placeholder(schema, path)
    else:
        raise SchemaError('invalid type', path)


def _generate_array_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.List[typing.Any]:
    """
    Generates a placeholder array object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object
    """
    if 'default' in schema:
        return typing.cast(typing.List[typing.Any], schema['default'])
    item_schema = schema['items']
    default_items = schema.get('defaultItems', schema.get('minItems', 0))
    return [
        generate_placeholder(item_schema, path + ['[?]'])
        for _ in range(default_items)
    ]


def _generate_tags_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Dict[str, typing.Any]:
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


def _generate_hazards_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Dict[str, typing.Any]:
    """
    Generate a placeholder GHS hazards object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object
    """
    return {
        '_type': 'hazards'
    }


def _generate_object_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Dict[str, typing.Any]:
    """
    Generates a placeholder object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object
    """
    if 'default' in schema:
        return typing.cast(typing.Dict[str, typing.Any], schema['default'])
    properties = schema['properties']
    return {
        property_name: generate_placeholder(property_schema, path + [property_name])
        for property_name, property_schema in properties.items()
    }


def _generate_bool_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Union[typing.Dict[str, typing.Any], None]:
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


def _generate_text_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Union[typing.Dict[str, typing.Any], None]:
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


def _generate_datetime_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Union[typing.Dict[str, typing.Any], None]:
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


def _generate_quantity_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Union[typing.Dict[str, typing.Any], None]:
    """
    Generates a placeholder quantity object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default magnitude (in base units)
    :raise SchemaError: if the units are invalid
    """
    if 'default' not in schema:
        return None
    if isinstance(schema['default'], dict):
        default = copy.deepcopy(schema['default'])
        if '_type' not in default:
            default['_type'] = 'quantity'
        validate(default, schema, path)   # fills missing values in quantity in place
        return default
    magnitude_in_base_units = schema['default']
    if isinstance(schema['units'], str):
        units = schema['units']
    else:
        units = schema['units'][0]

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


def _generate_sample_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Generates a placeholder sample object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there can be no default sample
    """
    return _generate_object_reference_placeholder(schema, path)


def _generate_measurement_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Generates a placeholder measurement object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there can be no default measurement
    """
    return _generate_object_reference_placeholder(schema, path)


def _generate_object_reference_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> None:
    """
    Generates a placeholder object reference object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there can be no default object reference
    """
    return None


def _generate_user_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Optional[typing.Dict[str, typing.Any]]:
    """
    Generates a placeholder user object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default user
    """
    if 'default' in schema:
        if schema['default'] == 'self' and current_user and current_user.is_authenticated:
            user_id = current_user.id
        elif type(schema['default']) is int:
            user_id = schema['default']
        else:
            user_id = None
        if user_id is not None:
            try:
                # ensure the user exists
                check_user_exists(user_id)
            except UserDoesNotExistError:
                pass
            else:
                return {
                    '_type': 'user',
                    'user_id': user_id
                }
    return None


def _generate_plotly_chart_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Union[typing.Dict[str, typing.Any], None]:
    """
    Generates a placeholder plotly_chart object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: the generated object or None, if there is no default text
    """
    return None


def _generate_timeseries_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Union[typing.Dict[str, typing.Any], None]:
    """
    Generates a placeholder timeseries object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there is currently no support for default timeseries
    """
    return None


def _generate_file_placeholder(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Optional[typing.Dict[str, typing.Any]]:
    """
    Generates a placeholder file object based on an object schema.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :return: None, as there is currently no support for default files
    """
    return None
