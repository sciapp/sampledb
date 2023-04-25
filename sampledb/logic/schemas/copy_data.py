# coding: utf-8
"""

"""

import typing
from .generate_placeholder import generate_placeholder


def copy_data(
        instance: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]],
        schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]]:
    if not schema.get('may_copy', True):
        return generate_placeholder(schema)
    if schema['type'] == 'file':
        return generate_placeholder(schema)
    if schema['type'] == 'array' and isinstance(instance, list):
        array_copy: typing.List[typing.Any] = []
        for item in instance:
            array_copy.append(copy_data(item, schema['items']))
        return array_copy
    if schema['type'] == 'object' and isinstance(instance, dict):
        object_copy: typing.Dict[str, typing.Any] = {}
        for property_name, property_schema in schema['properties'].items():
            if property_name in instance:
                object_copy[property_name] = copy_data(instance[property_name], property_schema)
            elif not property_schema.get('may_copy', True):
                object_copy[property_name] = generate_placeholder(property_schema)
        return object_copy
    return instance
