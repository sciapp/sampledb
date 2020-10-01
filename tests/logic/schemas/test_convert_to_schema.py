# coding: utf-8
"""

"""
import pytest

import sampledb
from sampledb.logic.schemas import validate, convert_to_schema
from sampledb.logic.schemas.generate_placeholder import SchemaError


def test_convert_same_schema():
    data = {
        '_type': 'text',
        'text': 'Example Text'
    }
    previous_schema = {
        'type': 'text',
        'title': 'Test'
    }
    new_schema = {
        'type': 'text',
        'title': 'Test'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings


def test_convert_same_type():
    data = {
        '_type': 'text',
        'text': 'Example Text'
    }
    previous_schema = {
        'type': 'text',
        'title': 'Test',
        'minLength': 1
    }
    new_schema = {
        'type': 'text',
        'title': 'Test'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings


def test_convert_object():
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example, Text'
        },
        'keywords': {
            '_type': 'text',
            'text': 'tag1, tag2'
        }
    }
    previous_schema = {
        'type': 'object',
        'title': 'Test',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'keywords': {
                'title': 'Keywords',
                'type': 'text'
            }
        }
    }
    new_schema = {
        'type': 'object',
        'title': 'Test',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'keywords': {
                'title': 'Keywords',
                'type': 'tags'
            }
        }
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == {
        'name': {
            '_type': 'text',
            'text': 'Example, Text'
        },
        'keywords': {
            '_type': 'tags',
            'tags': ['tag1', 'tag2']
        }
    }
    assert not warnings


def test_convert_schema_with_unknown_type():
    data = {}
    previous_schema = {
        'type': 'unknown',
        'title': 'Test'
    }
    new_schema = {
        'type': 'unknown',
        'title': 'Test'
    }
    with pytest.raises(SchemaError):
        convert_to_schema(data, previous_schema, new_schema)


def test_convert_incompatible_schemas():
    data = {
        '_type': 'text',
        'text': 'Example Text'
    }
    previous_schema = {
        'type': 'text',
        'title': 'Test'
    }
    new_schema = {
        'type': 'bool',
        'title': 'Test'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data is None
    assert warnings


def test_convert_text_to_tags():
    data = {
        '_type': 'text',
        'text': 'Tag1 ,Tag2,  Tag3'
    }
    previous_schema = {
        'type': 'text',
        'title': 'Test'
    }
    new_schema = {
        'type': 'tags',
        'title': 'Test'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == {
        '_type': 'tags',
        'tags': [
            'tag1', 'tag2', 'tag3'
        ]
    }
    assert not warnings


def test_convert_quantities_same_dimensionality():
    data = {
        '_type': 'quantity',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1,
        'units': 'm'
    }
    previous_schema = {
        'type': 'quantity',
        'title': 'Test',
        'units': 'm'
    }
    new_schema = {
        'type': 'quantity',
        'title': 'Test',
        'units': 'cm'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings


def test_convert_quantities_differing_dimensionality():
    data = {
        '_type': 'quantity',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1,
        'units': 'm'
    }
    previous_schema = {
        'type': 'quantity',
        'title': 'Test',
        'units': 'm'
    }
    new_schema = {
        'type': 'quantity',
        'title': 'Test',
        'units': 'ms'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data is None
    assert warnings


def test_convert_array():
    data = [
        {
            '_type': 'text',
            'text': 'Example, Text'
        },
        {
            '_type': 'text',
            'text': 'Example Text'
        }
    ]
    previous_schema = {
        'type': 'array',
        'title': 'Test',
        'items': {
            'type': 'text'
        }
    }
    new_schema = {
        'type': 'array',
        'title': 'Test',
        'items': {
            'type': 'tags'
        }
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == [
        {
            '_type': 'tags',
            'tags': ['example', 'text']
        },
        {
            '_type': 'tags',
            'tags': ['example text']
        }
    ]
    assert not warnings


def create_object_of_type(action_type_id):
    user = sampledb.logic.users.create_user(
        name='Example User',
        email='email@example.com',
        type=sampledb.logic.users.UserType.OTHER
    )
    action = sampledb.logic.actions.create_action(
        action_type_id=action_type_id,
        name='Example Action',
        description='',
        schema={
            'type': 'object',
            'title': 'Object Information',
            'properties': {
                'name': {
                    'type': 'text',
                    'title': 'Object Name'
                }
            },
            'required': ['name']
        }
    )
    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        },
        user_id=user.id
    )
    return object.id

def test_convert_sample_to_object_reference():
    object_id = create_object_of_type(sampledb.models.ActionType.SAMPLE_CREATION)
    data = {
        '_type': 'sample',
        'object_id': object_id
    }
    previous_schema = {
        'type': 'sample',
        'title': 'Test'
    }
    new_schema = {
        'type': 'object_reference',
        'title': 'Test'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': None
    }
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': sampledb.models.ActionType.SAMPLE_CREATION
    }
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': sampledb.models.ActionType.MEASUREMENT
    }
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data is None
    assert warnings


def test_convert_object_reference_to_sample():
    object_id = create_object_of_type(sampledb.models.ActionType.SAMPLE_CREATION)
    data = {
        '_type': 'object_reference',
        'object_id': object_id
    }
    previous_schema = {
        'type': 'object_reference',
        'title': 'Test'
    }
    new_schema = {
        'type': 'sample',
        'title': 'Test'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

    previous_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': None
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

    previous_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': sampledb.models.ActionType.SAMPLE_CREATION
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings


def test_convert_object_reference_to_measurement():
    object_id = create_object_of_type(sampledb.models.ActionType.MEASUREMENT)
    data = {
        '_type': 'object_reference',
        'object_id': object_id
    }
    previous_schema = {
        'type': 'object_reference',
        'title': 'Test'
    }
    new_schema = {
        'type': 'measurement',
        'title': 'Test'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

    previous_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': None
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

    previous_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': sampledb.models.ActionType.MEASUREMENT
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings
