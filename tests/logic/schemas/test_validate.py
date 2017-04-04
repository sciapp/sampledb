# coding: utf-8
"""

"""
import datetime
import pytest

from sampledb.logic.schemas import validate, ValidationError

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def test_validate_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'str'
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_missing_type():
    schema = {
        'title': 'Example',
        '_type': 'text'
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_invalid_schema_type():
    schema = [{
        'title': 'Example',
        'type': 'text'
    }]
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_invalid_instance_type():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = None
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    validate(instance, schema)


def test_validate_text_invalid():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_missing_key():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'text'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'text',
        'text': 'test',
        'locale': 'en_US'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ["A", "B", "C"]
    }
    instance = {
        '_type': 'text',
        'text': 'B'
    }
    validate(instance, schema)


def test_validate_text_invalid_choice():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ['A', 'B', 'C']
    }
    instance = {
        '_type': 'text',
        'text': 'D'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 1
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    validate(instance, schema)


def test_validate_text_invalid_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 10
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': 10
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    validate(instance, schema)


def test_validate_text_invalid_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': 1
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_invalid_text_type():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'text',
        'text': b'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'str',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'bool',
        'value': True
    }
    validate(instance, schema)


def test_validate_bool_invalid():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool_missing_key():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'bool'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'bool',
        'value': True,
        'default': True
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool_invalid_bool_type():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'bool',
        'value': 'True'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'boolean',
        'value': True
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1e-3
    }
    validate(instance, schema)


def test_validate_quantity_invalid():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_missing_key():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'magnitude_in_base_units': 1e-3
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1e-3,
        'default': True
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_quantity_dimensionality_type():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'dimensionality': b'[length]',
        'magnitude_in_base_units': 1e-3
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_quantity_units_type():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    instance = {
        '_type': 'quantity',
        'units': b'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1e-3
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_quantity_magnitude_type():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': '1e-3'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    instance = {
        '_type': 'Quantity',
        'units': 'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1e-3
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:30'
    }
    validate(instance, schema)


def test_validate_datetime_invalid_datetime():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:65'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_invalid():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_missing_key():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:30',
        'timezone': 'UTC+2'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_invalid_datetime_type():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime',
        'utc_datetime': datetime.datetime.now()
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'date',
        'utc_datetime': '2017-03-31 10:20:30'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_array():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    validate(instance, schema)


def test_validate_array_multiple_errors():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    instance = [
        {
            '_type': 'text'
        },
        {
            '_type': 'bool'
        },
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    with pytest.raises(ValidationError) as exc_info:
        validate(instance, schema)
    exception = exc_info.value
    assert len(exception.paths) == 2
    assert ['0'] in exception.paths
    assert ['1'] in exception.paths


def test_validate_array_invalid_instance_type():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_array_invalid_item_type():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    instance = [
        {
            '_type': 'bool',
            'value': True
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_array_min_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'minItems': 1
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    validate(instance, schema)


def test_validate_array_invalid_min_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'minItems': 2
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_array_max_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'maxItems': 1
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    validate(instance, schema)


def test_validate_array_invalid_max_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'maxItems': 0
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example Item',
                'type': 'text'
            }
        }
    }
    instance = {}
    validate(instance, schema)


def test_validate_object_multiple_errors():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example1': {
                'title': 'Example Item',
                'type': 'text'
            },
            'example2': {
                'title': 'Example Item',
                'type': 'text'
            }
        },
        'required': ['example1', 'example2']
    }
    instance = {
        'example2': {
            '_type': 'tect',
            'text': 'test'
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        validate(instance, schema)
    exception = exc_info.value
    assert len(exception.paths) == 2
    assert ['example1'] in exception.paths
    assert ['example2'] in exception.paths


def test_validate_object_invalid_instance_type():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example Item',
                'type': 'text'
            }
        }
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_required():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example Item',
                'type': 'text'
            }
        },
        'required': ['example']
    }
    instance = {
        'example': {
            '_type': 'text',
            'text': 'test'
        }
    }
    validate(instance, schema)


def test_validate_object_required_missing():
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
    instance = {}
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_unknown_property():
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
    instance = {
        'unknown': {
            '_type': 'text',
            'text': 'test'
        }
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_invalid_property():
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
    instance = {
        'example': {
            '_type': 'bool',
            'value': True
        }
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)
