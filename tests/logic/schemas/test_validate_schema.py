# coding: utf-8
"""

"""
import datetime
import pytest

from sampledb.logic.schemas import validate_schema
from sampledb.logic.errors import ValidationError
from sampledb.models import ActionType


def wrap_into_basic_schema(schema, name='other'):
    return {
        'title': "Basic Schema",
        'type': 'object',
        'properties': {
            'name': {
                'title': "Name",
                'type': 'text'
            },
            name: schema
        },
        'required': ['name']
    }


def test_validate_schema_invalid():
    schema = []
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_schema_missing_type():
    schema = {
        'title': 'Example'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_without_name():
    schema = {
        'title': "Basic Schema",
        'type': 'object',
        'properties': {
            'example': {
                'title': "Name",
                'type': 'text'
            }
        },
        'required': ['example']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_with_name_not_required():
    schema = {
        'title': "Basic Schema",
        'type': 'object',
        'properties': {
            'name': {
                'title': "Name",
                'type': 'text'
            }
        },
        'required': ['name']
    }
    validate_schema(schema)
    schema['required'].clear()
    with pytest.raises(ValidationError):
        validate_schema(schema)
    del schema['required']
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_schema_missing_title():
    schema = {
        'type': 'bool'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_schema_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'invalid'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))
    schema = {
        'title': 'Example',
        'type': b'bool'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_schema_invalid_title():
    schema = {
        'title': b'Example',
        'type': 'bool'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_bool_schema():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_bool_schema_default():
    schema = {
        'title': 'Example',
        'type': 'bool',
        'default': True
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_bool_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'bool',
        'default': 'true'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_bool_schema_note():
    schema = {
        'title': 'Example',
        'type': 'bool',
        'note': 'Example Note'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_bool_schema_invalid_note():
    schema = {
        'title': 'Example',
        'type': 'bool',
        'note': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_bool_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'bool',
        'value': 'true'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_schema():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_schema_note():
    schema = {
        'title': 'Example',
        'type': 'text',
        'note': 'Example Note'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_schema_invalid_note():
    schema = {
        'title': 'Example',
        'type': 'text',
        'note': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 1
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': 10
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ['A', 'B', 'C']
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_invalid_choice():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ['1', '2', 3]
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_invalid_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': '123'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_empty_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': []
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_pattern():
    schema = {
        'title': 'Example',
        'type': 'text',
        'pattern': '^[1-9][0-9]*/[A-Za-z]+$'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_invalid_pattern():
    schema = {
        'title': 'Example',
        'type': 'text',
        'pattern': '['
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_invalid_pattern_type():
    schema = {
        'title': 'Example',
        'type': 'text',
        'pattern': b'^[1-9][0-9]*/[A-Za-z]+$'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_invalid_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': "1"
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_negative_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': -1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_invalid_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': "10"
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_negative_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': -1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_min_and_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 1,
        'maxLength': 10
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_invalid_min_and_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 10,
        'maxLength': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_schema_default():
    schema = {
        'title': 'Example',
        'type': 'text',
        'default': 'test'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'text',
        'default': b'test'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_invalid_multiline_type():
    schema = {
        'title': 'Example',
        'type': 'text',
        'multiline': 'true'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_valid_multiline_type():
    schema = {
        'title': 'Example',
        'type': 'text',
        'multiline': True
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_datetime_schema():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_datetime_schema_default():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'default': '2017-03-31 10:20:30'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_datetime_schema_invalid_default_type():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'default': datetime.datetime.now()
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_datetime_schema_note():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'note': 'Example Note'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_datetime_schema_invalid_note_type():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'note': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_datetime_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'default': '2017-03-31 10:20'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_datetime_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:30'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_default():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': 1.5
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': '1.5'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_note():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'note': 'Example Note'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_invalid_note():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'note': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_invalid_units():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'invalid'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_invalid_units_type():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'magnitude_in_base_units': '1.5'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_missing_key():
    schema = {
        'title': 'Example',
        'type': 'quantity'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_array_schema():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    validate_schema(wrap_into_basic_schema(schema))


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
    validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_array_schema_missing_key():
    schema = {
        'title': 'Example',
        'type': 'array'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
    validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
    validate_schema(wrap_into_basic_schema(schema))


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
    validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
    validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_schema_with_property_order_duplicate_property():
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
        'propertyOrder': ['example1', 'example1']
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_schema_missing_key():
    schema = {
        'title': 'Example',
        'type': 'object'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
    validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


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
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_sample_schema():
    schema = {
        'title': 'Example',
        'type': 'sample',
        'note': 'Example Note'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_sample_schema_with_invalid_note():
    schema = {
        'title': 'Example',
        'type': 'sample',
        'note': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_sample_schema_without_note():
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_sample_schema_with_missing_title():
    schema = {
        'type': 'sample'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_sample_schema_with_unknown_property():
    schema = {
        'title': 'Example',
        'type': 'sample',
        'action_id': 0
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_measurement_schema():
    schema = {
        'title': 'Example',
        'type': 'measurement',
        'note': 'Example Note'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_measurement_schema_with_invalid_note():
    schema = {
        'title': 'Example',
        'type': 'measurement',
        'note': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_measurement_schema_without_note():
    schema = {
        'title': 'Example',
        'type': 'measurement'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_measurement_schema_with_missing_title():
    schema = {
        'type': 'measurement'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_measurement_schema_with_unknown_property():
    schema = {
        'title': 'Example',
        'type': 'measurement',
        'action_id': 0
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema():
    schema = {
        'title': 'Example',
        'type': 'object_reference',
        'note': 'Example Note',
        'action_type_id': ActionType.SAMPLE_CREATION
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema_with_invalid_note():
    schema = {
        'title': 'Example',
        'type': 'object_reference',
        'note': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema_without_note():
    schema = {
        'title': 'Example',
        'type': 'object_reference'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema_with_action_type_id_none():
    schema = {
        'title': 'Example',
        'type': 'object_reference',
        'note': 'Example Note',
        'action_type_id': None
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema_with_invalid_action_type_id():
    schema = {
        'title': 'Example',
        'type': 'object_reference',
        'action_type_id': 'measurement'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema_without_action_type_id():
    schema = {
        'title': 'Example',
        'type': 'object_reference'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema_with_missing_title():
    schema = {
        'type': 'object_reference'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema_with_unknown_property():
    schema = {
        'title': 'Example',
        'type': 'object_reference',
        'action_id': 0
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_schema_with_display_properties():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Property',
                'type': 'text'
            }
        },
        'required': ['name'],
        'displayProperties': ['name']
    }
    validate_schema(schema)


def test_validate_object_schema_with_invalid_display_properties():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Property',
                'type': 'text'
            }
        },
        'required': ['name'],
        'displayProperties': 'name'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_unknown_display_property():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Property',
                'type': 'text'
            }
        },
        'required': ['name'],
        'displayProperties': ['example']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_duplicate_display_property():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Property',
                'type': 'text'
            }
        },
        'required': ['name'],
        'displayProperties': ['name', 'name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_unknown_required_properties():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Property',
                'type': 'text'
            }
        },
        'required': ['name', 'example']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_duplicate_required_property():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Property',
                'type': 'text'
            }
        },
        'required': ['name', 'name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_nested_schema_with_display_properties():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Property',
                'type': 'text'
            },
            'example': {
                'title': 'Example Property',
                'type': 'object',
                'properties': {},
                'displayProperties': []
            }
        },
        'displayProperties': ['example']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_double_underscore_in_name():
    # To prevent name conflicts between properties, double underscores are not permitted in property names
    # They are used as separators for nested property names and property form field names
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Property',
                'type': 'text'
            },
            'property__1': {
                'title': 'Invalid Property Name',
                'type': 'text'
            }
        }
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_batch():
    schema = {
        'title': 'Example',
        'type': 'object',
        'batch': True,
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    validate_schema(schema)


def test_validate_object_schema_with_invalid_batch_value():
    schema = {
        'title': 'Example',
        'type': 'object',
        'batch': "true",
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_batch_not_in_toplevel():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'property': {
                'title': 'Property',
                'type': 'text',
                'batch': True
            }
        },
        'required': ['name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_batch_name_format():
    schema = {
        'title': 'Example',
        'type': 'object',
        'batch': True,
        'batch_name_format': "{:02d}",
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    validate_schema(schema)


def test_validate_object_schema_with_batch_name_format_but_without_batch():
    schema = {
        'title': 'Example',
        'type': 'object',
        'batch_name_format': "{:02d}",
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_object_schema_with_invalid_batch_name_format():
    schema = {
        'title': 'Example',
        'type': 'object',
        'batch': True,
        'batch_name_format': "{x}",
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_tags_schema():
    schema = {
        'title': 'Example',
        'type': 'tags'
    }
    validate_schema(wrap_into_basic_schema(schema, 'tags'))


def test_validate_tags_schema_default():
    schema = {
        'title': 'Example',
        'type': 'tags',
        'default': ['example']
    }
    validate_schema(wrap_into_basic_schema(schema, 'tags'))


def test_validate_tags_schema_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'tags',
        'default': [1]
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema, 'tags'))


def test_validate_tags_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'tags',
        'minItems': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema, 'tags'))


def test_hazards_in_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['name', 'hazards']
    }
    validate_schema(schema)


def test_hazards_with_note_in_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards',
                'note': 'This is a note'
            }
        },
        'required': ['name', 'hazards']
    }
    validate_schema(schema)


def test_misnamed_hazards_in_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'ghs': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['name', 'hazards']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_nested_hazards_in_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'nested': {
                'title': 'Nested Object',
                'type': 'object',
                'properties': {
                    'name': {
                        'title': 'Name',
                        'type': 'text'
                    },
                    'hazards': {
                        'title': 'GHS hazards',
                        'type': 'hazards'
                    }
                },
                'required': ['name', 'hazards']
            }
        },
        'required': ['name', 'hazards']
    }
    validate_schema(schema['properties']['nested'])
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_optional_hazards_in_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_hazards_with_extra_keys_in_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['name', 'hazards']
    }
    validate_schema(schema)
    schema['properties']['hazards']['default'] = []
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_hazards_with_missing_title_in_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['name', 'hazards']
    }
    validate_schema(schema)
    schema['properties']['hazards'].pop('title')
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_hazards_with_missing_type_in_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['name', 'hazards']
    }
    validate_schema(schema)
    schema['properties']['hazards'].pop('type')
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_notebook_templates():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': [
            {
                'url': 'notebook.ipynb',
                'title': 'notebook',
                'params': {}
            }
        ]
    }
    validate_schema(schema)


def test_notebook_templates_with_params():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': [
            {
                'url': 'notebook.ipynb',
                'title': 'notebook',
                'params': {
                    'object_id': 'object_id',
                    'name': ['name', 0],
                }
            }
        ]
    }
    validate_schema(schema)


def test_notebook_templates_with_invalid_params():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': [
            {
                'url': 'notebook.ipynb',
                'title': 'notebook',
                'params': []
            }
        ]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0]['params'] = {
        'object_id': 'object_ids',
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0]['params'] = {
        0: 'object_id',
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0]['params'] = {
        'name': ('name', 'text'),
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0]['params'] = {
        'name': 0,
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0]['params'] = {
        'name': ['name', b'text'],
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_notebook_templates_with_invalid_title():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': [
            {
                'url': 'notebook.py',
                'title': 0,
                'params': {}
            }
        ]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_notebook_templates_with_invalid_url():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': [
            {
                'url': None,
                'title': 'notebook',
                'params': {}
            }
        ]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0]['url'] = 'notebook.py'
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0]['url'] = '../notebook.ipynb'
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_notebook_templates_with_missing_keys():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': [
            None
        ]
    }
    schema['notebookTemplates'][0] = {
        'title': 'notebook',
        'params': {}
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0] = {
        'url': 'notebook.ipynb',
        'params': {}
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['notebookTemplates'][0] = {
        'url': 'notebook.ipynb',
        'title': 'test'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_notebook_templates_with_invalid_key():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': [
            {
                'url': 'notebook.ipynb',
                'title': 'test',
                'params': {},
                'other': 'value'
            }
        ]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_notebook_templates_with_invalid_type():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': {
            'test': {
                'url': 'notebook.ipynb',
                'title': 'test',
                'params': {}
            }
        }
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name'],
        'notebookTemplates': [
            [
                'notebook.ipynb', 'test', {}
            ]
        ]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_user_schema():
    schema = {
        'title': 'Example User',
        'type': 'user',
        'note': 'Example Note'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_user_schema_with_invalid_note():
    schema = {
        'title': 'Example User',
        'type': 'user',
        'note': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_user_schema_without_note():
    schema = {
        'title': 'Example User',
        'type': 'user'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_user_schema_with_missing_title():
    schema = {
        'type': 'user'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_user_schema_with_unknown_property():
    schema = {
        'title': 'Example User',
        'type': 'user',
        'user_role': 'example'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))
