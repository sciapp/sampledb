# coding: utf-8
"""
Implementation of convert_to_schema(data, previous_schema, new_schema)
"""

import typing

from flask_babel import _

from .generate_placeholder import generate_placeholder
from .utils import get_dimensionality_for_units
from ...models import ActionType
from .. import actions, errors, objects


def convert_to_schema(data: dict, previous_schema: dict, new_schema: dict) -> typing.Tuple[typing.Any, typing.Sequence[str]]:
    """
    Convert data from one schema to another.

    :param data: the sampledb object data
    :param previous_schema: the sampledb object schema for the given data
    :param new_schema: the target sampledb object schema
    :return: the converted data and a list of conversion warnings/notes
    """
    if new_schema == previous_schema and new_schema['type'] in ('bool', 'text', 'datetime', 'tags', 'sample', 'measurement', 'object_reference', 'quantity', 'array', 'objects', 'hazards'):
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
    if new_schema['type'] == 'object_reference' and previous_schema['type'] in ('sample', 'measurement'):
        action_type_compatible = False
        if 'action_type_id' in new_schema and new_schema['action_type_id'] is not None:
            if previous_schema['type'] == 'sample' and new_schema['action_type_id'] == ActionType.SAMPLE_CREATION:
                action_type_compatible = True
            if previous_schema['type'] == 'measurement' and new_schema['action_type_id'] == ActionType.MEASUREMENT:
                action_type_compatible = True
        else:
            action_type_compatible = True
        action_compatible = False
        if 'action_id' in new_schema and new_schema['action_id'] is not None:
            if 'object_id' in data:
                try:
                    referenced_object = objects.get_object(data['object_id'])
                    action_id = referenced_object.action_id
                except errors.ObjectDoesNotExistError:
                    pass
                else:
                    if action_id == new_schema['action_id']:
                        action_compatible = True
            else:
                action_compatible = True
        else:
            action_compatible = True
        if action_type_compatible and action_compatible:
            return {
                '_type': 'object_reference',
                'object_id': data['object_id']
            }, []
    if previous_schema['type'] == 'object_reference' and new_schema['type'] in ('sample', 'measurement'):
        if 'action_type_id' in previous_schema:
            if new_schema['type'] == 'sample' and previous_schema['action_type_id'] == ActionType.SAMPLE_CREATION:
                return data, []
            if new_schema['type'] == 'measurement' and previous_schema['action_type_id'] == ActionType.MEASUREMENT:
                return data, []
        if 'action_type_id' not in previous_schema or previous_schema['action_type_id'] is None:
            if 'object_id' in data:
                try:
                    referenced_object = objects.get_object(data['object_id'])
                    action = actions.get_action(referenced_object.action_id)
                    action_type_id = action.type_id
                except errors.ObjectDoesNotExistError:
                    pass
                except errors.ActionDoesNotExistError:
                    pass
                else:
                    if new_schema['type'] == 'sample' and action_type_id == ActionType.SAMPLE_CREATION:
                        return data, []
                    if new_schema['type'] == 'measurement' and action_type_id == ActionType.MEASUREMENT:
                        return data, []
    if previous_schema['type'] != new_schema['type']:
        return generate_placeholder(new_schema), [_("Unable to convert property '%(title)s' from type '%(type1)s' to type '%(type2)s'.", title=new_schema['title'], type1=previous_schema['type'], type2=new_schema['type'])]
    if new_schema['type'] in ('bool', 'text', 'datetime', 'tags', 'sample', 'measurement', 'hazards', 'user', 'plotly_chart'):
        return data, []
    if new_schema['type'] == 'object_reference':
        referenced_object = None
        action_type_compatible = 'action_type_id' not in new_schema or new_schema['action_type_id'] is None or ('action_type_id' in previous_schema and new_schema['action_type_id'] == previous_schema['action_type_id'])
        if not action_type_compatible and ('action_type_id' not in previous_schema or previous_schema['action_type_id'] is None):
            if 'object_id' in data:
                try:
                    referenced_object = objects.get_object(data['object_id'])
                    action = actions.get_action(referenced_object.action_id)
                    action_type_id = action.type_id
                except errors.ObjectDoesNotExistError:
                    pass
                except errors.ActionDoesNotExistError:
                    pass
                else:
                    if action_type_id == new_schema['action_type_id']:
                        action_type_compatible = True
            else:
                action_type_compatible = True
        action_compatible = 'action_id' not in new_schema or new_schema['action_id'] is None or ('action_id' in previous_schema and new_schema['action_id'] == previous_schema['action_id'])
        if not action_compatible and ('action_id' not in previous_schema or previous_schema['action_id'] is None):
            if 'object_id' in data:
                try:
                    if referenced_object is None:
                        referenced_object = objects.get_object(data['object_id'])
                    action_id = referenced_object.action_id
                except errors.ObjectDoesNotExistError:
                    pass
                else:
                    if action_id == new_schema['action_id']:
                        action_compatible = True
            else:
                action_compatible = True
        if action_type_compatible and action_compatible:
            return data, []
    if new_schema['type'] == 'quantity':
        previous_dimensionality = get_dimensionality_for_units(previous_schema['units'])
        new_dimensionality = get_dimensionality_for_units(new_schema['units'])
        if new_dimensionality == previous_dimensionality:
            return data, []
        return generate_placeholder(new_schema), [_("Unable to convert quantity '%(title)s' to different dimensionality: %(dimensionality1)s -> %(dimensionality2)s", title=new_schema['title'], dimensionality1=previous_dimensionality, dimensionality2=new_dimensionality)]
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
        for property_name in new_schema['properties']:
            # check if any properties were explicitly not set
            if property_name not in data and property_name not in new_schema.get('required', []) and property_name in previous_schema['properties']:
                del new_data[property_name]
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
    return generate_placeholder(new_schema), [_("Unable to convert property '%(title)s' of type '%(type)s'.", title=new_schema['title'], type=new_schema['type'])]
