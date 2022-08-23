# coding: utf-8
"""
Helper functions for conditional properties

New condition types also need to be implemented in JavaScript in:
sampledb/frontend/templates/objects/forms/conditional_wrapper_script.html
"""

import typing

from .validate_schema import ValidationError


def validate_condition_schema(
        condition: typing.Dict[str, typing.Any],
        property_schemas: typing.Dict[str, typing.Any],
        path: typing.List[str]
):
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
    elif condition['type'] == 'calculate':
        valid_keys = {'type', 'property_names', 'formula', 'digits'}
        required_keys = {'type', 'property_names', 'formula'}
        condition_keys = set(condition.keys())
        invalid_keys = condition_keys - valid_keys
        if invalid_keys:
            raise ValidationError('unexpected keys in condition: {}'.format(invalid_keys), path)
        missing_keys = required_keys - condition_keys
        if missing_keys:
            raise ValidationError('missing keys in condition: {}'.format(missing_keys), path)
        if not isinstance(condition['property_names'], list):
            raise ValidationError('property_names must be list', path)
        if not isinstance(condition['formula'], str):
            raise ValidationError('formula must be string', path)
        if 'digits' in condition and not isinstance(condition['digits'], int):
            raise ValidationError('digits must be an integer value', path)
        for property_name in condition['property_names']:
            if '__' in property_name:
                if property_name.split("__", 1)[0] not in property_schemas:
                    raise ValidationError('unknown property_name', path)
            else:
                if property_name not in property_schemas:
                    raise ValidationError('unknown property_name', path)
                if property_schemas[property_name].get('type') != 'quantity':
                    raise ValidationError('property_name does not belong to a quantity property', path)
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
            instance[condition['property_name']].get('text') == condition['choice']
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
    if condition['type'] == 'calculate':
        return (
            all(property_name in instance for property_name in condition['property_names'])
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
