# coding: utf-8
"""

"""

import pytest

from sampledb.logic.schemas import generate_placeholder
from sampledb.logic.errors import SchemaError


def test_generate_bool_object():
    object_schema = {
        'title': 'Example Boolean',
        'type': 'bool'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None


def test_generate_bool_object_default():
    object_schema = {
        'title': 'Example Boolean',
        'type': 'bool',
        'default': True
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'bool',
        'value': True
    }


def test_generate_text_object():
    object_schema = {
        'title': 'Example Text',
        'type': 'text'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None


def test_generate_text_object_default():
    object_schema = {
        'title': 'Example Text',
        'type': 'text',
        'default': 'test'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'text',
        'text': 'test'
    }


def test_generate_datetime_object():
    object_schema = {
        'title': 'Example Datetime',
        'type': 'datetime'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None


def test_generate_datetime_object_default():
    object_schema = {
        'title': 'Example Datetime',
        'type': 'datetime',
        'default': '2017-03-31 10:20:30'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:30'
    }


def test_generate_quantity_object():
    object_schema = {
        'title': 'Example Quantity',
        'type': 'quantity',
        'units': 'm'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None


def test_generate_quantity_object_default():
    object_schema = {
        'title': 'Example Quantity',
        'type': 'quantity',
        'units': 'm',
        'default': 1e-3
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'quantity',
        'dimensionality': '[length]',
        'units': 'm',
        'magnitude_in_base_units': 1e-3
    }


def test_generate_quantity_object_default_invalid_units():
    object_schema = {
        'title': 'Example Quantity',
        'type': 'quantity',
        'units': 'invalidß',
        'default': 1e-3
    }
    with pytest.raises(SchemaError):
        generate_placeholder(object_schema)


def test_generate_object():
    object_schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'example': {
                'type': 'text'
            }
        }
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {'example': None}


def test_generate_object_default():
    object_schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'example': {
                'type': 'text'
            }
        },
        'default': {
            'example': {
                '_type': 'text',
                'text': 'example'
            }
        }
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        'example': {
            '_type': 'text',
            'text': 'example'
        }
    }


def test_generate_object_property_default():
    object_schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'example': {
                'type': 'text',
                'default': 'example'
            }
        }
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        'example': {
            '_type': 'text',
            'text': 'example'
        }
    }


def test_generate_array():
    object_schema = {
        'title': 'Example Array',
        'type': 'array',
        'items': {
            'type': 'text'
        }
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == []


def test_generate_array_default():
    object_schema = {
        'title': 'Example Array',
        'type': 'array',
        'items': {
            'type': 'text'
        },
        'default': [{
            '_type': 'text',
            'text': 'example'
        }]
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == [{
        '_type': 'text',
        'text': 'example'
    }]


def test_generate_array_items_default():
    object_schema = {
        'title': 'Example Array',
        'type': 'array',
        'items': {
            'type': 'text',
            'default': 'example'
        },
        'minItems': 1
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == [{
        '_type': 'text',
        'text': 'example'
    }]


def test_generate_array_min_items():
    object_schema = {
        'title': 'Example Array',
        'type': 'array',
        'items': {
            'type': 'text'
        },
        'minItems': 1
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == [None]


def test_generate_missing_type():
    object_schema = {
    }
    with pytest.raises(SchemaError):
        generate_placeholder(object_schema)


def test_generate_invalid_type():
    object_schema = {
        'type': 'invalid'
    }
    with pytest.raises(SchemaError):
        generate_placeholder(object_schema)


def test_generate_sample_object():
    object_schema = {
        'title': 'Example Sample',
        'type': 'sample'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None


def test_generate_object_reference_object():
    object_schema = {
        'title': 'Example Object Reference',
        'type': 'object_reference'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None


def test_generate_tags():
    object_schema = {
        'title': 'Keywords',
        'type': 'tags'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'tags',
        'tags': []
    }


def test_generate_tags_default():
    object_schema = {
        'title': 'Keywords',
        'type': 'tags',
        'default': [
            'example'
        ]
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'tags',
        'tags': [
            'example'
        ]
    }


def test_generate_hazards():
    object_schema = {
        'title': 'GHS Hazards',
        'type': 'hazards'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'hazards'
    }


def test_generate_user_object():
    object_schema = {
        'title': 'Example User',
        'type': 'user'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None
