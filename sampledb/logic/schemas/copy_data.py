# coding: utf-8
"""

"""

import typing
from .generate_placeholder import generate_placeholder


def copy_data(
        instance: typing.Union[dict, list],
        schema: typing.Dict[str, typing.Any]
) -> typing.Union[dict, list]:
    if not schema.get('may_copy', True):
        return generate_placeholder(schema)
    if schema['type'] == 'array':
        copy = []
        for item in instance:
            copy.append(copy_data(item, schema['items']))
        return copy
    if schema['type'] == 'object':
        copy = {}
        for property_name, property_schema in schema['properties'].items():
            if property_name in instance:
                copy[property_name] = copy_data(instance[property_name], property_schema)
            elif not property_schema.get('may_copy', True):
                copy[property_name] = generate_placeholder(property_schema)
        return copy
    return instance
