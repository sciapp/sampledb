# coding: utf-8
"""

"""
import datetime
import pytest

from sampledb.logic.schemas import validate_schema, ValidationError

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def test_validate_schema_invalid():
    schema = []
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_schema_missing_type():
    schema = {
        'title': 'Example'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_schema_missing_title():
    schema = {
        'type': 'bool'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_schema_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'invalid'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema = {
        'title': 'Example',
        'type': b'bool'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_schema_invalid_title():
    schema = {
        'title': b'Example',
        'type': 'bool'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_bool_schema():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    validate_schema(schema)


def test_validate_bool_schema_default():
    schema = {
        'title': 'Example',
        'type': 'bool',
        'default': True
    }
    validate_schema(schema)


def test_validate_bool_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'bool',
        'default': 'true'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_bool_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'bool',
        'value': 'true'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_schema():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    validate_schema(schema)


def test_validate_text_with_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 1
    }
    validate_schema(schema)


def test_validate_text_with_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': 10
    }
    validate_schema(schema)


def test_validate_text_with_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ['A', 'B', 'C']
    }
    validate_schema(schema)


def test_validate_text_with_invalid_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ['1', '2', 3]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_with_empty_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': []
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_with_pattern():
    schema = {
        'title': 'Example',
        'type': 'text',
        'pattern': '^[1-9][0-9]*/[A-Za-z]+$'
    }
    validate_schema(schema)


def test_validate_text_with_invalid_pattern():
    schema = {
        'title': 'Example',
        'type': 'text',
        'pattern': '['
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_with_invalid_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': "1"
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_with_negative_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': -1
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_with_invalid_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': "10"
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_with_negative_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': -1
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_with_min_and_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 1,
        'maxLength': 10
    }
    validate_schema(schema)


def test_validate_text_invalid_min_and_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 10,
        'maxLength': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_schema_default():
    schema = {
        'title': 'Example',
        'type': 'text',
        'default': 'test'
    }
    validate_schema(schema)


def test_validate_text_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'text',
        'default': b'test'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_text_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_datetime_schema():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    validate_schema(schema)


def test_validate_datetime_schema_default():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'default': '2017-03-31 10:20:30'
    }
    validate_schema(schema)


def test_validate_datetime_schema_invalid_default_type():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'default': datetime.datetime.now()
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_datetime_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'default': '2017-03-31 10:20'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_datetime_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:30'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_quantity_schema():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    validate_schema(schema)


def test_validate_quantity_schema_default():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': 1.5
    }
    validate_schema(schema)


def test_validate_quantity_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': '1.5'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_quantity_schema_invalid_units():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'invalid'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_quantity_schema_invalid_units_type():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_quantity_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'magnitude_in_base_units': '1.5'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_quantity_schema_missing_key():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    validate_schema(schema)


def test_validate_array_schema_default():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'default': []
    }
    validate_schema(schema)


def test_validate_array_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'default': [1]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'min_items': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema_missing_key():
    schema = {
        'title': 'Example',
        'type': 'array'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema_invalid_min_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'minItems': -1
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema_invalid_min_items_type():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'minItems': 1.0
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema_invalid_max_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'maxItems': -1
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema_invalid_max_items_type():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'maxItems': 1.0
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema_invalid_min_max_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'minItems': 3,
        'maxItems': 2
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_array_schema_with_style():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'style': 'table'
    }
    validate_schema(schema)


def test_validate_array_schema_with_invalid_style():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'style': 'grid'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
            'title': 'Example',
                'type': 'text'
            }
        }
    }
    validate_schema(schema)


def test_validate_object_schema_default():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'default': {}
    }
    validate_schema(schema)


def test_validate_object_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'default': {
            'unknown': 1
        }
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_property_order():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example1': {
                'title': 'Example',
                'type': 'text'
            },
            'example2': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'propertyOrder': ['example1', 'example2']
    }
    validate_schema(schema)


def test_validate_object_schema_with_invalid_property_order():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example1': {
                'title': 'Example',
                'type': 'text'
            },
            'example2': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'propertyOrder': {0: 'example1', 1: 'example2'}
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_invalid_required():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'required': 'example'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_property_order_invalid_property():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example1': {
                'title': 'Example',
                'type': 'text'
            },
            'example2': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'propertyOrder': ['example1', 'example']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'additionalProperties': False
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_missing_key():
    schema = {
        'title': 'Example',
        'type': 'object'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_invalid_properties_type():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': [
            {
                'title': 'Example',
                'type': 'text'
            }
        ]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_required():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'required': ['example']
    }
    validate_schema(schema)


def test_validate_object_schema_required_unknown_property():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'required': ['unknown']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_default_missing_required_property():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'required': ['example'],
        'default': {}
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
