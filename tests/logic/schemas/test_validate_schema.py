# coding: utf-8
"""

"""
import datetime
import pytest

from sampledb.logic.schemas import validate_schema
from sampledb.logic.errors import ValidationError
from sampledb.models import ActionType


def wrap_into_basic_schema(schema, name='other', required=False):
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
        'required': ['name', name] if required else ['name']
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
    schema = {
        'title': {'en': b'Example'},
        'type': 'bool'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))
    schema = {
        'title': '',
        'type': 'bool'
    }
    validate_schema(wrap_into_basic_schema(schema))
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema), strict=True)
    schema = {
        'title': {'en': ''},
        'type': 'bool'
    }
    validate_schema(wrap_into_basic_schema(schema))
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema), strict=True)
    schema = {
        'title': ' ',
        'type': 'bool'
    }
    validate_schema(wrap_into_basic_schema(schema))
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema), strict=True)
    schema = {
        'title': {'en': ' '},
        'type': 'bool'
    }
    validate_schema(wrap_into_basic_schema(schema))
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema), strict=True)


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


def test_validate_text_schema_may_copy():
    schema = {
        'title': 'Example',
        'type': 'text',
        'may_copy': True
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_schema_may_copy_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'text',
        'may_copy': 'all'
    }
    with pytest.raises(ValidationError):
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


def test_validate_text_with_translated_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': [{'en': 'A', 'de': 'A2'}, {'en': 'B'}, {'en': 'C', 'de': 'C'}]
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_mixed_translated_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ['A', 'B', {'en': 'C'}]
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_translated_choices_without_english():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': [{'en': 'A', 'de': 'A2'}, {'en': 'B'}, {'de': 'C'}]
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


def test_validate_text_with_placeholder():
    schema = {
        'title': 'Example',
        'type': 'text',
        'placeholder': 'Placeholder'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_invalid_placeholder():
    schema = {
        'title': 'Example',
        'type': 'text',
        'placeholder': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_placeholder_and_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'placeholder': 'Placeholder',
        'choices': ['A', 'B', 'C']
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_text_with_translated_placeholder():
    schema = {
        'title': 'Example',
        'type': 'text',
        'placeholder': {'en': 'Placeholder', 'de': 'Platzhalter'}
    }
    validate_schema(wrap_into_basic_schema(schema))
    schema['placeholder']['xy'] = 'Placeholder'
    with pytest.raises(ValidationError):
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

    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': 15
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


def test_validate_quantity_schema_default_dict():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': {
            'magnitude': 1.5,
            'units': 'km'
        }
    }
    validate_schema(wrap_into_basic_schema(schema))

    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': {
            'magnitude': 1.5,
            'units': 'm'
        }
    }
    validate_schema(wrap_into_basic_schema(schema))

    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': {
            'magnitude_in_base_units': 1.5
        }
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_default_invalid_dict():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'default': {}
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))

    schema['default'] = {
        'magnitude': float('inf'),
        'units': 'km'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))

    schema['default'] = {
        'magnitude': 1.5,
        'units': 's'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))

    schema['default'] = {
        'magnitude_in_base_units': 1.5,
        'magnitude': 7
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


def test_validate_quantity_schema_multiple_units():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': ['m', 'km']
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_multiple_units_mismatched_dimensionality():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': ['mg', 'ms']
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_multiple_units_duplicates():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': ['m * s', 's * m']
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


def test_validate_quantity_schema_with_placeholder():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'placeholder': 'Placeholder'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_with_invalid_placeholder():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'placeholder': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_with_display_digits():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'display_digits': 2
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_with_invalid_display_digits():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'display_digits': .2
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))
    schema['display_digits'] = -1
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_min_magnitude():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'min_magnitude': 1.5
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_invalid_min_magnitude():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'min_magnitude': '1.5'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_max_magnitude():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'max_magnitude': 1.5
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_invalid_max_magnitude():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'max_magnitude': '1.5'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_min_and_max_magnitude():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'min_magnitude': 1.5,
        'max_magnitude': 1.5
    }
    validate_schema(wrap_into_basic_schema(schema))
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'min_magnitude': 1,
        'max_magnitude': 2
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_invalid_min_and_max_magnitude():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'min_magnitude': 2,
        'max_magnitude': 1
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_quantity_schema_min_and_max_magnitude_invalid_default():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm',
        'min_magnitude': 1,
        'max_magnitude': 2,
        'default': 1
    }
    validate_schema(wrap_into_basic_schema(schema))
    schema['default'] = 0.5
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))
    schema['default'] = 2.5
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


def test_validate_array_schema_default_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'defaultItems': 2
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_array_schema_invalid_default_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'defaultItems': '2'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))
    schema['defaultItems'] = -1
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))
    schema['defaultItems'] = 2
    schema['minItems'] = 2
    validate_schema(wrap_into_basic_schema(schema))
    schema['minItems'] = 3
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))
    schema['minItems'] = 0
    schema['maxItems'] = 2
    validate_schema(wrap_into_basic_schema(schema))
    schema['maxItems'] = 1
    with pytest.raises(ValidationError):
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
        'style': 1
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


def test_validate_object_reference_schema_with_action_id():
    schema = {
        'title': 'Example',
        'type': 'object_reference',
        'note': 'Example Note',
        'action_type_id': ActionType.SAMPLE_CREATION,
        'action_id': 1
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_object_reference_schema_with_invalid_action_id_type():
    schema = {
        'title': 'Example',
        'type': 'object_reference',
        'note': 'Example Note',
        'action_type_id': ActionType.SAMPLE_CREATION,
        'action_id': '1'
    }
    with pytest.raises(ValidationError):
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
        'object_id': 0
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


def test_validate_user_schema_with_default():
    schema = {
        'title': 'Example User',
        'type': 'user',
        'default': 'self'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_user_schema_with_invalid_default():
    schema = {
        'title': 'Example User',
        'type': 'user',
        'default': 'other'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_schemas_with_export_bool():
    schema = {
        'title': 'Example Property',
        'type': 'quantity',
        'units': '1',
        'dataverse_export': True
    }
    validate_schema(wrap_into_basic_schema(schema))

    for property_type in ('text', 'bool', 'user', 'sample', 'measurement', 'object_reference', 'datetime', 'tags', 'hazards'):
        schema = {
            'title': 'Example Property',
            'type': property_type,
            'dataverse_export': True
        }
        validate_schema(wrap_into_basic_schema(schema, property_type, required=True))

    schema = {
        'title': 'Example Property',
        'type': 'quantity',
        'units': '1',
        'dataverse_export': 'dataverse_export'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))

    for property_type in ('text', 'bool', 'user', 'sample', 'measurement', 'object_reference', 'datetime', 'tags', 'hazards'):
        schema = {
            'title': 'Example Property',
            'type': property_type,
            'dataverse_export': 'dataverse_export'
        }
        with pytest.raises(ValidationError):
            validate_schema(wrap_into_basic_schema(schema, property_type, required=True))


def test_schema_with_name_export():
    schema = {
        'title': "Basic Schema",
        'type': 'object',
        'properties': {
            'name': {
                'title': "Name",
                'type': 'text',
                'dataverse_export': False
            }
        },
        'required': ['name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['properties']['name']['dataverse_export'] = True
    validate_schema(schema)


def test_validate_plotly_chart_schema():
    schema = {
        'title': 'Example',
        'type': 'plotly_chart'
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_plotly_chart_schema_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'plotly_chart',
        'invalid Key': 'test'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_unknown_condition_type():
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
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
                'conditions': [
                    {
                        'type': 'choice_not_equals',
                        'property_name': 'example_choice',
                        'choice': {
                            'en': '1'
                        }
                    }
                ]
            }
        },
        'required': ['name']
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_required_conditional():
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
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
                'conditions': [
                    {
                        'type': 'choice_equals',
                        'property_name': 'example_choice',
                        'choice': {
                            'en': '1'
                        }
                    }
                ]
            }
        },
        'required': ['name', 'conditional_property']
    }
    validate_schema(schema)
    schema['properties']['name']['conditions'] = schema['properties']['conditional_property']['conditions']
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_choice_equals_conditions():
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
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
                'conditions': [
                    {
                        'type': 'choice_equals',
                        'property_name': 'example_choice',
                        'choice': {
                            'en': '1'
                        }
                    }
                ]
            }
        },
        'required': ['name']
    }

    for property_type in {'text', 'object_reference', 'sample', 'measurement', 'datetime', 'bool', 'user', 'plotly_chart'}:
        schema['properties']['conditional_property']['type'] = property_type
        validate_schema(schema)

    schema['properties']['conditional_property']['type'] = 'quantity'
    schema['properties']['conditional_property']['units'] = '1'
    validate_schema(schema)
    del schema['properties']['conditional_property']['units']

    for property_type in {'hazards', 'tags'}:
        schema['properties']['conditional_property']['type'] = property_type
        with pytest.raises(ValidationError):
            validate_schema(schema)

    schema['properties']['conditional_property']['type'] = 'array'
    schema['properties']['conditional_property']['items'] = {
        'title': 'test',
        'type': 'text'
    }
    validate_schema(schema)
    del schema['properties']['conditional_property']['items']

    schema['properties']['conditional_property']['type'] = 'object'
    schema['properties']['conditional_property']['properties'] = {
        'test':{
            'title': 'test',
            'type': 'text'
        }
    }
    validate_schema(schema)
    del schema['properties']['conditional_property']['properties']

    schema['properties']['conditional_property']['type'] = 'text'
    schema['properties']['conditional_property']['conditions'][0]['choice']['en'] = '3'
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_recipe():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": [
            {
                "name": "Recipe 1",
                "property_values": {
                    "text": {"text": "Text 1", "_type": "text"},
                    "choice": {"text": "Option 1", "_type": "text"},
                    "quantity": {"magnitude_in_base_units": 123.321, "_type": "quantity"},
                    "boolean": {"value": True, "_type": "bool"},
                    "timestamp": {"utc_datetime": "2022-04-05 09:07:00", "_type": "datetime"}
                }
            }
        ],
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "text": {
                "title": "Text",
                "type": "text"
            },
            "choice": {
                "title": "Choice",
                "type": "text",
                "choices": ["Option 1", "Option 2", "Option 3", "Option 4"]
            },
            "quantity": {
                "title": "Quantity",
                "type": "quantity",
                "units": "nm"
            },
            "boolean": {
                "title": "Boolean",
                "type": "bool",
                "default": False
            },
            "timestamp": {
                "title": "Timestamp",
                "type": "datetime"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "text", "choice", "quantity", "boolean", "timestamp"]
    }
    validate_schema(schema)

    schema['recipes'][0]['quantity'] = {"magnitude": 123, "units": "nm", "_type": "quantity"}
    validate_schema(schema)

    schema['properties']['quantity']['units'] = ['nm', 'mm', 'm']
    validate_schema(schema)

    schema['recipes'][0]['property_values'] = {
        "text": None,
        "choice": None,
        "quantity": None,
        "timestamp": None
    }
    validate_schema(schema)


def test_validate_recipe_invalid_type():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": {},
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name"]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_recipe_invalid_name():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": [
            {
                "property_values": {"text": {"text": "Text 1", "_type": "text"}}
            }
        ],
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "text": {
                "title": "Text",
                "type": "text"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "text"]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['name'] = 123
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['name'] = {'en': 'Recipe 1', 'se': 'recept 1'}
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['name'] = {'en': 'Recipe 1', 'de': False}
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['name'] = {'de': 'Rezept 1'}
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_recipe_invalid_text():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": [
            {
                "name": "Recipe 1",
                "property_values": {"text": {"_type": "text", "text": 123}}
            }
        ],
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "text": {
                "title": "Text",
                "type": "text"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "text"]
    }

    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['property_values']['text']['text'] = {'en': 'Recipe 1', 'se': 'recept 1'}
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['property_values']['text']['text'] = {'en': 'Recipe 1', 'de': False}
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_recipe_invalid_choice():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": [
            {
                "name": "Recipe 1",
                "property_values": {"choice": {"_type": "text", "text": "Option 42"}}
            }
        ],
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "choice": {
                "title": "Choice",
                "type": "text",
                "choices": ["Option 1", "Option 2", "Option 3", "Option 4"]
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "choice"]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_recipe_invalid_quantity():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": [
            {
                "name": "Recipe 1",
                "property_values": {"quantity": {"_type": "quantity", "magnitude": "Not a number"}}
            }
        ],
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "quantity": {
                "title": "Quantity",
                "type": "quantity",
                "units": "nm"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "quantity"]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['property_values']['quantity']['magnitude'] = 1
    schema['recipes'][0]['property_values']['quantity']['units'] = 'cm'  # invalid unit
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['properties']['quantity']['units'] = ['nm', 'm']  # units array, cm still invalid
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['property_values']['quantity'] = {
        'magnitude_in_base_units': 1,
        "_type": "quantity"
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_recipe_invalid_boolean():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": [
            {
                "name": "Recipe 1",
                "property_values": {"boolean": {"_type": "bool", "value": "Not a number"}}
            }
        ],
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "boolean": {
                "title": "Boolean",
                "type": "bool"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "boolean"]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_recipe_invalid_datetime():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": [
            {
                "name": "Recipe 1",
                "property_values": {"timestamp": {"_type": "datetime", "utc_datetime": 541997}}
            }
        ],
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "timestamp": {
                "title": "Timestamp",
                "type": "datetime"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "timestamp"]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['property_values']['timestamp']['datetime'] = '09:07:00 2022-04-05'
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_recipe_invalid_properties():
    schema = {
        "title": "Recipe",
        "type": "object",
        "recipes": [
            {
                "name": "Recipe 1"
            }
        ],
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "timestamp": {
                "title": "Timestamp",
                "type": "datetime"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "timestamp"]
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['recipes'][0]['property_values'] = {"invalid_property": {"_type": "quantity", "magnitude": 42}}
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_invalid_property_names_schema():
    schema = {
        "title": "Example",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            }
        },
        "required": ["name"],
        "propertyOrder": ["name"]
    }

    schema["properties"]["test1"] = {
        "title": "Test",
        "type": "text"
    }
    validate_schema(schema)
    validate_schema(schema, strict=True)
    del schema["properties"]["test1"]

    schema["properties"]["te__st"] = {
        "title": "Test",
        "type": "text"
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    with pytest.raises(ValidationError):
        validate_schema(schema, strict=True)
    del schema["properties"]["te__st"]

    schema["properties"][""] = {
        "title": "Test",
        "type": "text"
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    with pytest.raises(ValidationError):
        validate_schema(schema, strict=True)
    del schema["properties"][""]

    schema["properties"]["test_"] = {
        "title": "Test",
        "type": "text"
    }
    validate_schema(schema)
    with pytest.raises(ValidationError):
        validate_schema(schema, strict=True)
    del schema["properties"]["test_"]

    schema["properties"]["1test"] = {
        "title": "Test",
        "type": "text"
    }
    validate_schema(schema)
    with pytest.raises(ValidationError):
        validate_schema(schema, strict=True)
    del schema["properties"]["1test"]

    schema["properties"]["te.st"] = {
        "title": "Test",
        "type": "text"
    }
    validate_schema(schema)
    with pytest.raises(ValidationError):
        validate_schema(schema, strict=True)
    del schema["properties"]["te.st"]


def test_validate_show_more():
    schema = {
        "title": "Example",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "quantity": {
                "title": "Quantity",
                "type": "quantity",
                "units": "1"
            },
            "text": {
                "title": "Text",
                "type": "text",
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "quantity", "text"],
        "show_more": ["quantity"]
    }

    validate_schema(schema)

    schema['show_more'] = 'quantity'
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['show_more'] = ['quant']
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_file_schema():
    schema = {
        'title': 'Example File',
        'type': 'file',
        'note': 'Example Note',
        'preview': True
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_file_schema_with_invalid_property():
    schema = {
        'title': 'Example File',
        'type': 'file',
        'note': 'Example Note',
        'extension': '.txt'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_file_schema_with_extensions():
    schema = {
        'title': 'Example File',
        'type': 'file',
        'note': 'Example Note',
        'extensions': ['.txt']
    }
    validate_schema(wrap_into_basic_schema(schema))


def test_validate_file_schema_with_invalid_extensions():
    schema = {
        'title': 'Example File',
        'type': 'file',
        'note': 'Example Note',
        'extensions': [1]
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_file_schema_with_invalid_preview():
    schema = {
        'title': 'Example File',
        'type': 'file',
        'preview': 'small'
    }
    with pytest.raises(ValidationError):
        validate_schema(wrap_into_basic_schema(schema))


def test_validate_workflow_show_more():
    schema = {
        "title": "Example",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "quantity": {
                "title": "Quantity",
                "type": "quantity",
                "units": "1"
            },
            "text": {
                "title": "Text",
                "type": "text",
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "quantity", "text"],
        "workflow_show_more": ["quantity"]
    }

    validate_schema(schema)

    schema['workflow_show_more'] = 'quantity'
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['workflow_show_more'] = ['quant']
    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_validate_workflow_view():
    schema = {
        "title": "Example",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "quantity": {
                "title": "Quantity",
                "type": "quantity",
                "units": "1"
            },
            "text": {
                "title": "Text",
                "type": "text",
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "quantity", "text"],
        "workflow_view": {
            "referencing_action_type_id": 1,
            "referencing_action_id": [1],
            "referenced_action_type_id": [ActionType.SAMPLE_CREATION],
            "referenced_action_id": 1
        }
    }

    validate_schema(schema)

    schema['workflow_view']['key'] = 'value'
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['workflow_view']['referencing_action_type_id'] = 'MEASUREMENT'
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['workflow_view']['referencing_action_id'] = 'Action'
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['workflow_view']['referenced_action_type_id'] = 'MEASUREMENT'
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['workflow_view']['referenced_action_id'] = 'Action'
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['workflow_view']['referencing_action_id'] = [ActionType.MEASUREMENT, False]
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['workflow_view']['referenced_action_type_id'] = [1, None]
    with pytest.raises(ValidationError):
        validate_schema(schema)

    schema['workflow_view']['referenced_action_id'] = [-99, False]
    with pytest.raises(ValidationError):
        validate_schema(schema)
