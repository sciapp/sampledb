# coding: utf-8
"""

"""
import pytest

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
