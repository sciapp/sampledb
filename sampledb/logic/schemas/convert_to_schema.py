# coding: utf-8
"""
Implementation of convert_to_schema(data, previous_schema, new_schema)
"""

import typing
from .generate_placeholder import generate_placeholder
from .utils import get_dimensionality_for_units


def convert_to_schema(data: dict, previous_schema: dict, new_schema: dict) -> typing.Tuple[typing.Any, typing.Sequence[str]]:
    """
    Convert data from one schema to another.

    :param data: the sampledb object data
    :param previous_schema: the sampledb object schema for the given data
    :param new_schema: the target sampledb object schema
    :return: the converted data and a list of conversion warnings/notes
    """
    if new_schema == previous_schema and new_schema['type'] in ('bool', 'text', 'datetime', 'tags', 'sample', 'measurement', 'quantity', 'array', 'objects', 'hazards'):
        return data, []

    if new_schema['type'] == 'tags' and previous_schema['type'] == 'text':
        tags = []
        for tag in data['text'].split(','):
            tag = tag.strip().lower()
            if tag not in tags:
                tags.append(tag)
        new_data = {
            '_type': 'tags',
            'tags': tags
        }
        return new_data, []
    if previous_schema['type'] != new_schema['type']:
        return generate_placeholder(new_schema), ["Unable to convert property '{}' from type '{}' to type '{}'.".format(new_schema['title'], previous_schema['type'], new_schema['type'])]
    if new_schema['type'] in ('bool', 'text', 'datetime', 'tags', 'sample', 'measurement', 'hazards'):
        return data, []
    if new_schema['type'] == 'quantity':
        previous_dimensionality = get_dimensionality_for_units(previous_schema['units'])
        new_dimensionality = get_dimensionality_for_units(new_schema['units'])
        if new_dimensionality == previous_dimensionality:
            return data, []
        return generate_placeholder(new_schema), ["Unable to convert quantity '{}' to different dimensionality: {} -> {}".format(new_schema['title'], previous_dimensionality, new_dimensionality)]
    if new_schema['type'] == 'object':
        upgrade_warnings = []
        new_data = generate_placeholder(new_schema)
        for property_name, property_value in data.items():
            if property_name in new_schema['properties']:
                new_property_value, property_upgrade_warnings = convert_to_schema(property_value, previous_schema['properties'][property_name], new_schema['properties'][property_name])
                if new_property_value is not None:
                    new_data[property_name] = new_property_value
                for upgrade_warning in property_upgrade_warnings:
                    if upgrade_warning not in upgrade_warnings:
                        upgrade_warnings.append(upgrade_warning)
        return new_data, upgrade_warnings
    if new_schema['type'] == 'array':
        new_data = []
        upgrade_warnings = []
        for item in data:
            new_item, item_upgrade_warnings = convert_to_schema(item, previous_schema['items'], new_schema['items'])
            new_data.append(new_item)
            for upgrade_warning in item_upgrade_warnings:
                if upgrade_warning not in upgrade_warnings:
                    upgrade_warnings.append(upgrade_warning)
        return new_data, upgrade_warnings
    return generate_placeholder(new_schema), ["Unable to convert property '{}' of type '{}'.".format(new_schema['title'], new_schema['type'])]
