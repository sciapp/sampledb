# coding: utf-8
"""

"""
import dataclasses
import inspect

import pytest

from sampledb.logic.schemas import generate_placeholder, get_default_data, validate_schema
from sampledb.logic.errors import SchemaError
import sampledb.logic
import sampledb.models


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


def test_generate_quantity_object_default_multiple_units():
    object_schema = {
        'title': 'Example Quantity',
        'type': 'quantity',
        'units': ['mm', 'm'],
        'default': 1e-3
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'quantity',
        'dimensionality': '[length]',
        'units': 'mm',
        'magnitude_in_base_units': 1e-3
    }


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


def test_generate_array_with_default_items():
    object_schema = {
        'title': 'Example Array',
        'type': 'array',
        'items': {
            'type': 'text'
        },
        "defaultItems": 2
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == [None, None]


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


def test_generate_user_object_with_default_self(flask_server):
    user = sampledb.logic.users.create_user(
        name='Test',
        email='test@example.org',
        type=sampledb.models.UserType.PERSON
    )
    object_schema = {
        'title': 'Example User',
        'type': 'user',
        'default': 'self'
    }

    @dataclasses.dataclass
    class MockUser:
        id: int
        is_authenticated: bool

    # mock current user to avoid being dependent on the request context
    generate_placeholder_module = inspect.getmodule(sampledb.logic.schemas.generate_placeholder)
    previous_current_user = generate_placeholder_module.current_user

    generate_placeholder_module.current_user = MockUser(id=user.id, is_authenticated=True)
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'user',
        'user_id': user.id
    }

    generate_placeholder_module.current_user = MockUser(id=-1, is_authenticated=False)
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None
    generate_placeholder_module.current_user = previous_current_user


def test_generate_user_object_with_default_user_id():
    user = sampledb.logic.users.create_user(
        name='Test',
        email='test@example.org',
        type=sampledb.models.UserType.PERSON
    )
    object_schema = {
        'title': 'Example User',
        'type': 'user',
        'default': user.id
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object == {
        '_type': 'user',
        'user_id': user.id
    }


def test_generate_plotly_chart_object():
    object_schema = {
        'title': 'Plot',
        'type': 'plotly_chart'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None


def test_generate_file_object():
    object_schema = {
        'title': 'Example File',
        'type': 'file'
    }
    placeholder_object = generate_placeholder(object_schema)
    assert placeholder_object is None


def test_get_default_data_object():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    validate_schema(schema)
    assert get_default_data(schema, ()) == {'name': None}
    assert get_default_data(schema, ('name',)) is None
    assert get_default_data(schema, ('other',)) is None

    schema['properties']['name']['default'] = {'en': 'Default'}
    validate_schema(schema)
    assert get_default_data(schema, ()) == {
        'name': {
            '_type': 'text',
            'text': {'en': 'Default'}
        }
    }
    assert get_default_data(schema, ('name',)) == {
        '_type': 'text',
        'text': {'en': 'Default'}
    }
    assert get_default_data(schema, ('other',)) is None

    schema['default'] = {
        'name': {
            '_type': 'text',
            'text': {'en': 'Other Default'}
        }
    }
    validate_schema(schema)
    assert get_default_data(schema, ()) == {
        'name': {
            '_type': 'text',
            'text': {'en': 'Other Default'}
        }
    }
    assert get_default_data(schema, ('name',)) == {
        '_type': 'text',
        'text': {'en': 'Other Default'}
    }
    assert get_default_data(schema, ('other',)) is None


def test_get_default_data_array():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'array': {
                'title': 'Array',
                'type': 'array',
                'items': {
                    'title': 'Entry',
                    'type': 'text'
                }
            }
        },
        'required': ['name']
    }
    validate_schema(schema)
    assert get_default_data(schema, ()) == {'name': None, 'array': []}
    assert get_default_data(schema, ('name',)) is None
    assert get_default_data(schema, ('array',)) == []
    assert get_default_data(schema, ('array', 0)) is None
    assert get_default_data(schema, ('other',)) is None

    schema['properties']['array']['items']['default'] = {'en': 'Entry Default'}
    validate_schema(schema)
    assert get_default_data(schema, ()) == {'name': None, 'array': []}
    assert get_default_data(schema, ('name',)) is None
    assert get_default_data(schema, ('array',)) == []
    assert get_default_data(schema, ('array', 0)) == {
        '_type': 'text',
        'text': {'en': 'Entry Default'}
    }
    assert get_default_data(schema, ('other',)) is None

    schema['properties']['array']['default'] = [
        {
            '_type': 'text',
            'text': {'en': '1st Entry Default'}
        },
        {
            '_type': 'text',
            'text': {'en': '2nd Entry Default'}
        }
    ]
    validate_schema(schema)
    assert get_default_data(schema, ()) == {
        'name': None,
        'array': [
            {
                '_type': 'text',
                'text': {'en': '1st Entry Default'}
            },
            {
                '_type': 'text',
                'text': {'en': '2nd Entry Default'}
            }
        ]
    }
    assert get_default_data(schema, ('array',)) == [
        {
            '_type': 'text',
            'text': {'en': '1st Entry Default'}
        },
        {
            '_type': 'text',
            'text': {'en': '2nd Entry Default'}
        }
    ]
    assert get_default_data(schema, ('array', 0)) == {
        '_type': 'text',
        'text': {'en': '1st Entry Default'}
    }
    assert get_default_data(schema, ('array', 1)) == {
        '_type': 'text',
        'text': {'en': '2nd Entry Default'}
    }
    assert get_default_data(schema, ('array', 2)) == {
        '_type': 'text',
        'text': {'en': 'Entry Default'}
    }


def test_get_default_data_object_array():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'array': {
                'title': 'Array',
                'type': 'array',
                'items': {
                    'title': 'Entry',
                    'type': 'object',
                    'properties': {
                        'value': {
                            'title': 'Value',
                            'type': 'text'
                        }
                    }
                }
            }
        },
        'required': ['name']
    }
    validate_schema(schema)
    assert get_default_data(schema, ()) == {'name': None, 'array': []}
    assert get_default_data(schema, ('name',)) is None
    assert get_default_data(schema, ('array',)) == []
    assert get_default_data(schema, ('array', 0)) == {'value': None}
    assert get_default_data(schema, ('array', 0, 'value')) is None

    schema['properties']['array']['items']['properties']['value']['default'] = 'Default Value'
    validate_schema(schema)
    assert get_default_data(schema, ()) == {'name': None, 'array': []}
    assert get_default_data(schema, ('name',)) is None
    assert get_default_data(schema, ('array',)) == []
    assert get_default_data(schema, ('array', 0)) == {
        'value': {
            '_type': 'text',
            'text': 'Default Value'
        }
    }
    assert get_default_data(schema, ('array', 0, 'value')) == {
        '_type': 'text',
        'text': 'Default Value'
    }

    schema['default'] = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'array': [
            {}
        ]
    }
    validate_schema(schema)
    assert get_default_data(schema, ()) == {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'array': [
            {}
        ]
    }
    assert get_default_data(schema, ('name',)) == {
        '_type': 'text',
        'text': 'Name'
    }
    assert get_default_data(schema, ('array',)) == [
        {}
    ]
    assert get_default_data(schema, ('array', 0)) == {}
    assert get_default_data(schema, ('array', 0, 'value')) is None
