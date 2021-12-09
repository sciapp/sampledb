# coding: utf-8

import pytest

from sampledb.logic.schemas.conditions import is_condition_fulfilled, are_conditions_fulfilled, validate_condition_schema, ValidationError


def test_validate_unknown_condition():
    property_schemas = {
        'example_choice': {
            'title': 'Example Choice',
            'type': 'text',
            'choices': [
                {
                    'en': '1'
                },
                {
                    'en': '2'
                }
            ]
        },
        'conditional_property': {
            'title': 'Conditional Property',
            'type': 'text',
        }
    }
    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'unknown',
                'property_name': 'example_choice'
            },
            property_schemas,
            ['conditional_property', '0']
        )


def test_validate_choice_equals_condition():
    property_schemas = {
        'example_choice': {
            'title': 'Example Choice',
            'type': 'text',
            'choices': [
                {
                    'en': '1'
                },
                {
                    'en': '2'
                }
            ]
        },
        'conditional_property': {
            'title': 'Conditional Property',
            'type': 'text',
        }
    }
    validate_condition_schema(
        {
            'type': 'choice_equals',
            'property_name': 'example_choice',
            'choice': {
                'en': '1'
            }
        },
        property_schemas,
        ['conditional_property', '0']
    )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'choice_equals',
                'property_name': 'example_choice',
                'choice': {
                    'en': '3'
                }
            },
            property_schemas,
            ['conditional_property', '0']
        )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'choice_equals',
                'property_name': 'example_choice'
            },
            property_schemas,
            ['conditional_property', '0']
        )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'choice_equals',
                'property_name': 'unknown_property',
                'choice': {
                    'en': '1'
                }
            },
            property_schemas,
            ['conditional_property', '0']
        )


def test_validate_user_equals_condition():
    property_schemas = {
        'example_user': {
            'title': 'Example User',
            'type': 'user'
        },
        'conditional_property': {
            'title': 'Conditional Property',
            'type': 'text',
        }
    }
    validate_condition_schema(
        {
            'type': 'user_equals',
            'property_name': 'example_user',
            'user_id': None
        },
        property_schemas,
        ['conditional_property', '0']
    )
    validate_condition_schema(
        {
            'type': 'user_equals',
            'property_name': 'example_user',
            'user_id': 1
        },
        property_schemas,
        ['conditional_property', '0']
    )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'user_equals',
                'property_name': 'unknown_property'
            },
            property_schemas,
            ['conditional_property', '0']
        )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'user_equals',
                'property_name': 'example_user',
                'user_id': "1"
            },
            property_schemas,
            ['conditional_property', '0']
        )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'user_equals',
            },
            property_schemas,
            ['conditional_property', '0']
        )


def test_validate_bool_equals_condition():
    property_schemas = {
        'example_bool': {
            'title': 'Example Bool',
            'type': 'bool'
        },
        'conditional_property': {
            'title': 'Conditional Property',
            'type': 'text',
        }
    }
    validate_condition_schema(
        {
            'type': 'bool_equals',
            'property_name': 'example_bool',
            'value': True
        },
        property_schemas,
        ['conditional_property', '0']
    )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'bool_equals',
                'property_name': 'unknown_property',
                'bool': True
            },
            property_schemas,
            ['conditional_property', '0']
        )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'bool_equals',
                'property_name': 'example_bool',
                'bool': None
            },
            property_schemas,
            ['conditional_property', '0']
        )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'bool_equals'
            },
            property_schemas,
            ['conditional_property', '0']
        )


def test_validate_object_equals_condition():
    property_schemas = {
        'example_object': {
            'title': 'Example Object',
            'type': 'object_reference'
        },
        'conditional_property': {
            'title': 'Conditional Property',
            'type': 'text',
        }
    }
    validate_condition_schema(
        {
            'type': 'object_equals',
            'property_name': 'example_object',
            'object_id': None
        },
        property_schemas,
        ['conditional_property', '0']
    )
    validate_condition_schema(
        {
            'type': 'object_equals',
            'property_name': 'example_object',
            'object_id': 1
        },
        property_schemas,
        ['conditional_property', '0']
    )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'object_equals',
                'property_name': 'unknown_property'
            },
            property_schemas,
            ['conditional_property', '0']
        )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'object_equals',
                'property_name': 'example_object',
                'object_id': "1"
            },
            property_schemas,
            ['conditional_property', '0']
        )

    with pytest.raises(ValidationError):
        validate_condition_schema(
            {
                'type': 'object_equals',
            },
            property_schemas,
            ['conditional_property', '0']
        )


def test_is_unknown_condition_fulfilled():
    instance = {}
    assert not is_condition_fulfilled(
        {
            'type': 'unknown'
        },
        instance
    )


def test_is_choice_equals_condition_fulfilled():
    instance = {
        'example_choice': {
            '_type': 'text',
            'text': {
                'en': '1'
            }
        }
    }
    assert is_condition_fulfilled(
        {
            'type': 'choice_equals',
            'property_name': 'example_choice',
            'choice': {
                'en': '1'
            }
        },
        instance
    )
    assert not is_condition_fulfilled(
        {
            'type': 'choice_equals',
            'property_name': 'example_choice',
            'choice': {
                'en': '2'
            }
        },
        instance
    )
    assert not is_condition_fulfilled(
        {
            'type': 'choice_equals',
            'property_name': 'example_choice',
            'choice': {
                'en': '1'
            }
        },
        {}
    )


def test_is_user_equals_condition_fulfilled():
    assert is_condition_fulfilled(
        {
            'type': 'user_equals',
            'property_name': 'example_user',
            'user_id': None
        },
        {}
    )
    assert not is_condition_fulfilled(
        {
            'type': 'user_equals',
            'property_name': 'example_user',
            'user_id': 1
        },
        {}
    )
    assert is_condition_fulfilled(
        {
            'type': 'user_equals',
            'property_name': 'example_user',
            'user_id': 1
        },
        {
            'example_user': {
                '_type': 'user',
                'user_id': 1
            }
        }
    )


def test_is_bool_equals_condition_fulfilled():
    assert is_condition_fulfilled(
        {
            'type': 'bool_equals',
            'property_name': 'example_bool',
            'value': True
        },
        {
            'example_bool': {
                '_type': 'bool',
                'value': True
            }
        }
    )
    assert not is_condition_fulfilled(
        {
            'type': 'bool_equals',
            'property_name': 'example_bool',
            'value': False
        },
        {
            'example_bool': {
                '_type': 'bool',
                'value': True
            }
        }
    )


def test_is_object_equals_condition_fulfilled():
    assert is_condition_fulfilled(
        {
            'type': 'object_equals',
            'property_name': 'example_object',
            'object_id': None
        },
        {}
    )
    assert not is_condition_fulfilled(
        {
            'type': 'object_equals',
            'property_name': 'example_object',
            'object_id': 1
        },
        {}
    )
    assert is_condition_fulfilled(
        {
            'type': 'object_equals',
            'property_name': 'example_object',
            'object_id': 1
        },
        {
            'example_object': {
                '_type': 'object_reference',
                'object_id': 1
            }
        }
    )


def test_are_no_conditions_fulfilled():
    assert are_conditions_fulfilled(None, {})


def test_are_choice_equals_conditions_fulfilled():
    instance = {
        'example_choice': {
            '_type': 'text',
            'text': {
                'en': '1'
            }
        }
    }
    assert are_conditions_fulfilled(
        [
            {
                'type': 'choice_equals',
                'property_name': 'example_choice',
                'choice': {
                    'en': '1'
                }
            }
        ],
        instance
    )
    assert not are_conditions_fulfilled(
        [
            {
                'type': 'choice_equals',
                'property_name': 'example_choice',
                'choice': {
                    'en': '1'
                }
            },
            {
                'type': 'choice_equals',
                'property_name': 'example_choice',
                'choice': {
                    'en': '2'
                }
            }
        ],
        instance
    )
