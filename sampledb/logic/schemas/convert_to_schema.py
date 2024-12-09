# coding: utf-8
"""
Implementation of convert_to_schema(data, previous_schema, new_schema)
"""
import copy
import typing

from flask_babel import _

from .generate_placeholder import generate_placeholder
from .utils import get_dimensionality_for_units
from ..utils import get_translated_text
from ...models import ActionType
from .. import actions, errors, objects


def convert_to_schema(
        data: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any],
        new_schema: typing.Dict[str, typing.Any]
) -> typing.Tuple[typing.Any, typing.Sequence[str]]:
    """
    Convert data from one schema to another.

    :param data: the sampledb object data
    :param previous_schema: the sampledb object schema for the given data
    :param new_schema: the target sampledb object schema
    :return: the converted data and a list of conversion warnings/notes
    """
    result: typing.Optional[typing.Tuple[typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[str]]], typing.Sequence[str]]]

    if new_schema == previous_schema and new_schema['type'] in ('bool', 'text', 'datetime', 'tags', 'sample', 'measurement', 'object_reference', 'quantity', 'array', 'objects', 'hazards', 'timeseries', 'file'):
        return data, []

    if new_schema['type'] == 'tags' and previous_schema['type'] == 'text' and isinstance(data, dict):
        result = _try_convert_text_to_tags(data)
        if result:
            return result
    if new_schema['type'] == 'object_reference' and previous_schema['type'] in ('sample', 'measurement'):
        result = _try_convert_legacy_object_reference_to_object_reference(data, new_schema, previous_schema)
        if result:
            return result
    if previous_schema['type'] == 'object_reference' and new_schema['type'] in ('sample', 'measurement'):
        result = _try_convert_object_reference_to_legacy_object_reference(data, new_schema, previous_schema)
        if result:
            return result
    if previous_schema['type'] != new_schema['type']:
        return copy.deepcopy(generate_placeholder(new_schema)), [_("Unable to convert property '%(title)s' from type '%(type1)s' to type '%(type2)s'.", title=get_translated_text(new_schema['title']), type1=previous_schema['type'], type2=new_schema['type'])]
    if new_schema['type'] == 'text' and 'choices' in new_schema and isinstance(data, dict):
        result = _try_convert_text_to_choices(data, new_schema)
        if result:
            return result
    if new_schema['type'] in ('bool', 'text', 'datetime', 'tags', 'sample', 'measurement', 'hazards', 'user', 'plotly_chart', 'file'):
        return data, []
    if new_schema['type'] == 'object_reference':
        result = _try_convert_object_reference_to_object_reference(data, new_schema, previous_schema)
        if result:
            return result
    if new_schema['type'] == 'quantity':
        result = _try_convert_quantity_to_quantity(data, new_schema, previous_schema)
        if result:
            return result
    if previous_schema['type'] == 'timeseries':
        result = _try_convert_timeseries_to_timeseries(data, new_schema, previous_schema)
        if result:
            return result
    if new_schema['type'] == 'object':
        result = _try_convert_object_to_object(data, new_schema, previous_schema)
        if result:
            return result
    if new_schema['type'] == 'array' and isinstance(data, list):
        result = _try_convert_array_to_array(data, new_schema, previous_schema)
        if result:
            return result
    return copy.deepcopy(generate_placeholder(new_schema)), [_("Unable to convert property '%(title)s' of type '%(type)s'.", title=get_translated_text(new_schema['title']), type=new_schema['type'])]


def _try_convert_text_to_tags(
        data: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.Dict[str, typing.Any], typing.Sequence[str]]]:
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


def _try_convert_text_to_choices(
        data: typing.Dict[str, typing.Any],
        new_schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.Optional[typing.Dict[str, typing.Any]], typing.Sequence[str]]]:
    warning_text = _("Unable to convert property '%(title)s' of type '%(type)s'.", title=get_translated_text(new_schema['title']), type=new_schema['type'])
    if set(data.keys()) != {'_type', 'text'}:
        return None, [warning_text]
    if data['text'] in new_schema['choices']:
        return data, []
    dict_text = data['text'] if isinstance(data['text'], dict) else {'en': data['text']}
    dict_choices = [
        choice if isinstance(choice, dict) else {'en': choice}
        for choice in new_schema['choices']
    ]
    matching_choices = [
        choice_index
        for choice_index, choice in enumerate(dict_choices)
        if all(
            lang_code not in choice or choice[lang_code] == dict_text[lang_code]
            for lang_code in dict_text
        )
    ]
    if len(matching_choices) == 1:
        new_data = copy.deepcopy(data)
        new_data['text'] = new_schema['choices'][matching_choices[0]]
        return new_data, []
    return None, [warning_text]


def _try_convert_object_to_object(
        data: typing.Dict[str, typing.Any],
        new_schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.Dict[str, typing.Any], typing.Sequence[str]]]:
    upgrade_warnings = []
    new_data = copy.deepcopy(generate_placeholder(new_schema))
    if not isinstance(new_data, dict):
        return None
    for property_name, property_value in data.items():
        if property_name in new_schema['properties']:
            new_property_value, property_upgrade_warnings = convert_to_schema(
                data=property_value,
                previous_schema=previous_schema['properties'][property_name],
                new_schema=new_schema['properties'][property_name]
            )
            if new_property_value is not None:
                new_data[property_name] = new_property_value
            for upgrade_warning in property_upgrade_warnings:
                if upgrade_warning not in upgrade_warnings:
                    upgrade_warnings.append(upgrade_warning)
    for property_name in new_schema['properties']:
        # check if any properties were explicitly not set
        if property_name in new_data and property_name not in data and property_name not in new_schema.get('required', []) and property_name in previous_schema['properties']:
            del new_data[property_name]
    return new_data, upgrade_warnings


def _try_convert_array_to_array(
        data: typing.List[typing.Any],
        new_schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.List[typing.Any], typing.Sequence[str]]]:
    new_data = []
    upgrade_warnings = []
    for item in data:
        new_item, item_upgrade_warnings = convert_to_schema(item, previous_schema['items'], new_schema['items'])
        new_data.append(new_item)
        for upgrade_warning in item_upgrade_warnings:
            if upgrade_warning not in upgrade_warnings:
                upgrade_warnings.append(upgrade_warning)
    return new_data, upgrade_warnings


def _try_convert_quantity_to_quantity(
        data: typing.Dict[str, typing.Any],
        new_schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[str]]], typing.Sequence[str]]]:
    previous_dimensionality = get_dimensionality_for_units(previous_schema['units'])
    new_dimensionality = get_dimensionality_for_units(new_schema['units'])
    if new_dimensionality == previous_dimensionality:
        return data, []
    return generate_placeholder(new_schema), [_("Unable to convert quantity '%(title)s' to different dimensionality: %(dimensionality1)s -> %(dimensionality2)s", title=get_translated_text(new_schema['title']), dimensionality1=previous_dimensionality, dimensionality2=new_dimensionality)]


def _try_convert_timeseries_to_timeseries(
        data: typing.Dict[str, typing.Any],
        new_schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.List[str]]], typing.Sequence[str]]]:
    previous_dimensionality = get_dimensionality_for_units(previous_schema['units'])
    new_dimensionality = get_dimensionality_for_units(new_schema['units'])
    if new_dimensionality == previous_dimensionality:
        return data, []
    return generate_placeholder(new_schema), [_("Unable to convert timeseries '%(title)s' to different dimensionality: %(dimensionality1)s -> %(dimensionality2)s", title=get_translated_text(new_schema['title']), dimensionality1=previous_dimensionality, dimensionality2=new_dimensionality)]


def _try_convert_object_reference_to_object_reference(
        data: typing.Dict[str, typing.Any],
        new_schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.Dict[str, typing.Any], typing.Sequence[str]]]:
    referenced_object = None
    action_type_compatible = 'action_type_id' not in new_schema or new_schema['action_type_id'] is None or ('action_type_id' in previous_schema and new_schema['action_type_id'] == previous_schema['action_type_id'])
    if not action_type_compatible and ('action_type_id' not in previous_schema or previous_schema['action_type_id'] is None):
        if 'object_id' in data:
            try:
                referenced_object = objects.get_object(data['object_id'])
                if referenced_object.action_id is None:
                    action_type_id = None
                else:
                    action = actions.get_action(referenced_object.action_id)
                    action_type_id = action.type_id
            except errors.ObjectDoesNotExistError:
                pass
            except errors.ActionDoesNotExistError:
                pass
            else:
                if action_type_id is not None:
                    if isinstance(new_schema['action_type_id'], int) and action_type_id == new_schema['action_type_id']:
                        action_type_compatible = True
                    if isinstance(new_schema['action_type_id'], list) and action_type_id in new_schema['action_type_id']:
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
                if action_id is not None:
                    if isinstance(new_schema['action_id'], int) and action_id == new_schema['action_id']:
                        action_compatible = True
                    if isinstance(new_schema['action_id'], list) and action_id in new_schema['action_id']:
                        action_compatible = True
        else:
            action_compatible = True
    if action_type_compatible and action_compatible:
        return data, []
    if (action_type_compatible or action_compatible) and new_schema.get('filter_operator', 'and') == 'or':
        return data, []
    return None


def _try_convert_object_reference_to_legacy_object_reference(
        data: typing.Dict[str, typing.Any],
        new_schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.Dict[str, typing.Any], typing.Sequence[str]]]:
    if 'action_type_id' in previous_schema:
        if new_schema['type'] == 'sample' and previous_schema['action_type_id'] == ActionType.SAMPLE_CREATION:
            return data, []
        if new_schema['type'] == 'measurement' and previous_schema['action_type_id'] == ActionType.MEASUREMENT:
            return data, []
    if 'action_type_id' not in previous_schema or previous_schema['action_type_id'] is None:
        if 'object_id' in data:
            try:
                referenced_object = objects.get_object(data['object_id'])
                if referenced_object.action_id is None:
                    action_type_id = None
                else:
                    action = actions.get_action(referenced_object.action_id)
                    action_type_id = action.type_id
            except errors.ObjectDoesNotExistError:
                pass
            except errors.ActionDoesNotExistError:
                pass
            else:
                if action_type_id is not None:
                    if new_schema['type'] == 'sample' and action_type_id == ActionType.SAMPLE_CREATION:
                        return data, []
                    if new_schema['type'] == 'measurement' and action_type_id == ActionType.MEASUREMENT:
                        return data, []
    return None


def _try_convert_legacy_object_reference_to_object_reference(
        data: typing.Dict[str, typing.Any],
        new_schema: typing.Dict[str, typing.Any],
        previous_schema: typing.Dict[str, typing.Any]
) -> typing.Optional[typing.Tuple[typing.Dict[str, typing.Any], typing.Sequence[str]]]:
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
    if (action_type_compatible or action_compatible) and new_schema.get('filter_operator', 'and') == 'or':
        return {
            '_type': 'object_reference',
            'object_id': data['object_id']
        }, []
    return None
