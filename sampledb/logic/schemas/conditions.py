# coding: utf-8
"""
Helper functions for conditional properties

New condition types also need to be implemented in JavaScript in:
sampledb/static/sampledb/js/conditional_wrapper.js
"""

import typing

from ..errors import ValidationError, ObjectDoesNotExistError
from .. import objects


def validate_condition_schema(
        condition: typing.Dict[str, typing.Any],
        property_schemas: typing.Dict[str, typing.Any],
        path: typing.List[str]
) -> None:
    """
    Validate a condition from a property schema.

    :param condition: the condition to validate
    :param property_schemas: the schemas of all properties of the parent object
    :param path: the path to the condition
    :raise ValidationError: if the condition is invalid
    """
    if condition['type'] == 'choice_equals':
        if set(condition.keys()) != {'type', 'property_name', 'choice'}:
            raise ValidationError('expected type, property_name and choice in condition', path)
        if condition['property_name'] not in property_schemas:
            raise ValidationError('unknown property_name', path)
        if property_schemas[condition['property_name']].get('type') != 'text' or (condition['choice'] is not None and condition['choice'] not in property_schemas[condition['property_name']].get('choices', [])):
            raise ValidationError('unknown choice', path)
    elif condition['type'] == 'user_equals':
        if set(condition.keys()) != {'type', 'property_name', 'user_id'}:
            raise ValidationError('expected type, property_name and user_id in condition', path)
        if condition['property_name'] not in property_schemas:
            raise ValidationError('unknown property_name', path)
        if property_schemas[condition['property_name']].get('type') != 'user':
            raise ValidationError('property_name does not belong to a user property', path)
        if condition['user_id'] is not None and not isinstance(condition['user_id'], int):
            raise ValidationError('user_id must be integer or None', path)
    elif condition['type'] == 'bool_equals':
        if set(condition.keys()) != {'type', 'property_name', 'value'}:
            raise ValidationError('expected type, property_name and value in condition', path)
        if condition['property_name'] not in property_schemas:
            raise ValidationError('unknown property_name', path)
        if property_schemas[condition['property_name']].get('type') != 'bool':
            raise ValidationError('property_name does not belong to a bool property', path)
        if not isinstance(condition['value'], bool):
            raise ValidationError('value must be boolean', path)
    elif condition['type'] == 'object_equals':
        if set(condition.keys()) != {'type', 'property_name', 'object_id'}:
            raise ValidationError('expected type, property_name and object_id in condition', path)
        if condition['property_name'] not in property_schemas:
            raise ValidationError('unknown property_name', path)
        if property_schemas[condition['property_name']].get('type') not in {'object_reference', 'sample', 'measurement'}:
            raise ValidationError('property_name does not belong to a object_reference, sample or measurement property', path)
        if condition['object_id'] is not None and not isinstance(condition['object_id'], int):
            raise ValidationError('object_id must be integer or None', path)
    elif condition['type'] == 'action_equals':
        if set(condition.keys()) != {'type', 'property_name', 'action_id'}:
            raise ValidationError('expected type, property_name and action_id in condition', path)
        if condition['property_name'] not in property_schemas:
            raise ValidationError('unknown property_name', path)
        if property_schemas[condition['property_name']].get('type') not in {'object_reference', 'sample', 'measurement'}:
            raise ValidationError('property_name does not belong to a object_reference, sample or measurement property', path)
        if condition['action_id'] is not None and not isinstance(condition['action_id'], int):
            raise ValidationError('action_id must be integer or None', path)
    elif condition['type'] in ('any', 'all'):
        if set(condition.keys()) != {'type', 'conditions'}:
            raise ValidationError('expected type and conditions in condition', path)
        if not isinstance(condition['conditions'], list):
            raise ValidationError('conditions must be list', path)
        for i, sub_condition in enumerate(condition['conditions']):
            validate_condition_schema(sub_condition, property_schemas, path + [str(i)])
    elif condition['type'] == 'not':
        if set(condition.keys()) != {'type', 'condition'}:
            raise ValidationError('expected type and condition in condition', path)
        validate_condition_schema(condition['condition'], property_schemas, path + ['condition'])
    else:
        raise ValidationError('unknown condition type', path)


def is_condition_fulfilled(
        condition: typing.Dict[str, typing.Any],
        instance: typing.Dict[str, typing.Any]
) -> bool:
    """
    Check whether a particular condition is fulfilled by the parent object.

    :param condition: the condition to check
    :param instance: the instance to check the condition on
    :return: whether or not the condition is fulfilled
    """
    if condition['type'] == 'choice_equals':
        return (
            condition['choice'] is None and
            condition['property_name'] not in instance
        ) or (
            condition['choice'] is not None and
            condition['property_name'] in instance and
            isinstance(instance[condition['property_name']], dict) and
            (
                instance[condition['property_name']].get('text') == condition['choice'] or
                instance[condition['property_name']].get('text') == {'en': condition['choice']} or
                {'en': instance[condition['property_name']].get('text')} == condition['choice']
            )
        )
    if condition['type'] == 'user_equals':
        return (
            condition['user_id'] is None and
            condition['property_name'] not in instance
        ) or (
            condition['user_id'] is not None and
            condition['property_name'] in instance and
            isinstance(instance[condition['property_name']], dict) and
            instance[condition['property_name']].get('user_id') == condition['user_id']
        )
    if condition['type'] == 'bool_equals':
        return (
            condition['value'] is not None and
            condition['property_name'] in instance and
            isinstance(instance[condition['property_name']], dict) and
            instance[condition['property_name']].get('value') == condition['value']
        )
    if condition['type'] == 'object_equals':
        return (
            condition['object_id'] is None and
            condition['property_name'] not in instance
        ) or (
            condition['object_id'] is not None and
            condition['property_name'] in instance and
            isinstance(instance[condition['property_name']], dict) and
            instance[condition['property_name']].get('object_id') == condition['object_id']
        )
    if condition['type'] == 'action_equals':
        def get_action_id_or_none(object_id: typing.Any) -> int | None:
            if type(object_id) is not int:
                return None
            try:
                object = objects.get_object(object_id)
            except ObjectDoesNotExistError:
                return None
            return object.action_id
        return (
            condition['action_id'] is None and
            condition['property_name'] not in instance
        ) or (
            condition['property_name'] in instance and
            isinstance(instance[condition['property_name']], dict) and
            get_action_id_or_none(instance[condition['property_name']].get('object_id')) == condition['action_id']
        )
    if condition['type'] == 'any':
        for sub_condition in condition['conditions']:
            if is_condition_fulfilled(sub_condition, instance):
                return True
        # any without passing conditions is considered False
        return False
    if condition['type'] == 'all':
        for sub_condition in condition['conditions']:
            if not is_condition_fulfilled(sub_condition, instance):
                return False
        # all without failing conditions is considered True
        return True
    if condition['type'] == 'not':
        return not is_condition_fulfilled(condition['condition'], instance)

    # unknown or unfulfillable condition
    return False


def are_conditions_fulfilled(
        conditions: typing.Optional[typing.List[typing.Dict[str, typing.Any]]],
        instance: typing.Dict[str, typing.Any]
) -> bool:
    """
    Check whether a list of conditions are fulfilled by the parent object.

    :param conditions: the list of conditions to check, or None
    :param instance: the instance to check the conditions on
    :return: whether or not all condition are fulfilled
    """
    return conditions is None or all(
        is_condition_fulfilled(condition, instance)
        for condition in conditions
    )
