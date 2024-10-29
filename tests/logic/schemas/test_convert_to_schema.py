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
    assert new_data == {
        '_type': 'object_reference',
        'object_id': object_id
    }
    assert not warnings

    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': None
    }
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == {
        '_type': 'object_reference',
        'object_id': object_id
    }
    assert not warnings

    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': sampledb.models.ActionType.SAMPLE_CREATION
    }
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == {
        '_type': 'object_reference',
        'object_id': object_id
    }
    assert not warnings

    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_type_id': sampledb.models.ActionType.MEASUREMENT
    }
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data is None
    assert warnings

    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_id': sampledb.logic.objects.get_object(object_id).action_id
    }
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == {
        '_type': 'object_reference',
        'object_id': object_id
    }
    assert not warnings

    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_id': sampledb.logic.objects.get_object(object_id).action_id + 1
    }
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data is None
    assert warnings

@pytest.mark.parametrize('old_type', ['sample', 'measurement', 'object_reference'])
@pytest.mark.parametrize(
    [
        'action_id_match',
        'action_type_id_match',
        'filter_operator',
        'success'
    ],
    [
        (True, True, 'and', True),
        (True, False, 'and', False),
        (False, True, 'and', False),
        (False, False, 'and', False),
        (True, True, 'or', True),
        (True, False, 'or', True),
        (False, True, 'or', True),
        (False, False, 'or', False),
        (None, None, 'and', True),
        (None, False, 'and', False),
        (False, None, 'and', False),
        (False, False, 'and', False),
        (None, None, 'or', True),
        (None, False, 'or', True),
        (False, None, 'or', True),
        (False, False, 'or', False),
    ]
)
def test_convert_object_reference_with_filter_operator(old_type, action_id_match, action_type_id_match, filter_operator, success):
    object_id = create_object_of_type({
        'sample': sampledb.models.ActionType.SAMPLE_CREATION,
        'measurement': sampledb.models.ActionType.MEASUREMENT,
        'object_reference': sampledb.models.ActionType.SAMPLE_CREATION,
    }.get(old_type))
    data = {
        '_type': old_type,
        'object_id': object_id
    }
    previous_schema = {
        'type': old_type,
        'title': 'Test'
    }
    new_schema = {
        'type': 'object_reference',
        'title': 'Test',
        'action_id': sampledb.logic.objects.get_object(object_id).action_id + (0 if action_id_match else 1),
        'action_type_id': sampledb.logic.actions.get_action(sampledb.logic.objects.get_object(object_id).action_id).type_id + (0 if action_type_id_match else 1),
        'filter_operator': filter_operator
    }
    if action_id_match is None:
        del new_schema['action_id']
    if action_type_id_match is None:
        del new_schema['action_type_id']
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    if success:
        assert new_data == {
            '_type': 'object_reference',
            'object_id': object_id
        }
        assert not warnings
    else:
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


def test_convert_schema_missing_values():
    data = {}
    previous_schema = {
        'type': 'object',
        'properties': {
            'text': {
                'title': 'Text',
                'type': 'text'
            }
        }
    }
    new_schema = {
        'type': 'object',
        'properties': {
            'text': {
                'title': 'Text2',
                'type': 'text'
            }
        }
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings


def test_convert_timeseries_schema():
    data = {
        "data": [
            [
                "2020-01-02 03:04:05.678910",
                1,
                1
            ]
        ],
        "_type": "timeseries",
        "units": "m",
        "dimensionality": "[length]"
    }
    previous_schema = {
        "type": "timeseries",
        "title": {
            "en": "Test Title"
        },
        "units": [
            "m",
            "km"
        ],
        "display_digits": 15
    }
    new_schema = {
        "title": {
            "en": "Test Title"
        },
        "note": {
            "en": ""
        },
        "type": "timeseries",
        "units": "m",
        "display_digits": 3
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

def test_convert_timeseries_schema_changed_dimensionality():
    data = {
        "data": [
            [
                "2020-01-02 03:04:05.678910",
                1,
                1
            ]
        ],
        "_type": "timeseries",
        "units": "m",
        "dimensionality": "[length]"
    }
    previous_schema = {
        "type": "timeseries",
        "title": {
            "en": "Test Title"
        },
        "units": [
            "m",
            "km"
        ],
        "display_digits": 15
    }
    new_schema = {
        "title": {
            "en": "Test Title"
        },
        "note": {
            "en": ""
        },
        "type": "timeseries",
        "units": "min",
        "display_digits": 3
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data is None
    assert warnings == ["Unable to convert timeseries 'Test Title' to different dimensionality: [length] -> [time]"]


def test_convert_file_schema():
    data = {
        '_type': 'file',
        'file_id': 0
    }
    previous_schema = {
        'type': 'file',
        'title': 'Example File'
    }
    new_schema = {
        'type': 'file',
        'title': 'Example File'
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings

    new_schema = {
        'type': 'file',
        'title': 'Example File',
        'extensions': ['.txt']
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == data
    assert not warnings


@pytest.mark.parametrize("previous_text, expected_new_text, previous_choices, new_choices", [
    ("A", "A", ["A", "B"], ["A", "B", "C"]),
    ("A", "A", ["A", "B"], ["A"]),
    ("A", None, ["A", "B"], ["B"]),
    ("A", {"en": "A"}, ["A", "B"], [{"en": "A"}, {"en": "B"}, {"en": "C"}]),
    ("A", {"en": "A"}, ["A", "B"], [{"en": "A"}]),
    ("A", None, ["A", "B"], [{"en": "B"}]),
    ("A", "A", ["A", "B"], ["A", {"en": "A"}]),
    ("A", None, ["A", "B"], [{"en": "B", "de": "A"}]),
    ({"en": "A"}, {"en": "A"}, [{"en": "A"}, {"en": "B"}], [{"en": "A"}, {"en": "B"}, {"en": "C"}]),
    ({"en": "A"}, {"en": "A"}, [{"en": "A"}, {"en": "B"}], [{"en": "A"}]),
    ({"en": "A"}, None, [{"en": "A"}, {"en": "B"}], [{"en": "B"}]),
    ({"en": "A"}, "A", [{"en": "A"}, {"en": "B"}], ["A", "B", "C"]),
    ({"en": "A"}, "A", [{"en": "A"}, {"en": "B"}], ["A"]),
    ({"en": "A"}, None, [{"en": "A"}, {"en": "B"}], ["B"]),
    ({"en": "A"}, {"en": "A", "de": "A_de"}, [{"en": "A"}, {"en": "B"}], [{"en": "A", "de": "A_de"}, {"en": "B", "de": "B_de"}]),
    ({"en": "A"}, {"en": "A", "de": "A_de"}, [{"en": "A"}, {"en": "B"}], [{"en": "A", "de": "A_de"}]),
    ({"en": "A"}, None, [{"en": "A"}, {"en": "B"}], [{"en": "B", "de": "B_de"}]),
    ({"en": "A"}, None, [{"en": "A"}, {"en": "B"}], [{"en": "B", "de": "A"}]),
    ({"en": "A"}, None, [{"en": "A"}, {"en": "B"}], [{"en": "A", "de": "A1_de"}, {"en": "A", "de": "A2_de"}]),
    ({"en": "A", "de": "A_de"}, {"en": "A"}, [{"en": "A", "de": "A_de"}], [{"en": "A"}]),
    ({"en": "A", "de": "A_de"}, "A", [{"en": "A", "de": "A_de"}], ["A"]),
    ({"en": "A", "de": "A_de"}, None, [{"en": "A", "de": "A_de"}], ["A", "A"]),
    ({"en": "A", "de": "A1_de"}, None, [{"en": "A", "de": "A1_de"}, {"en": "A", "de": "A2_de"}], [{"en": "A", "de": "A_de1"}, {"en": "A", "de": "A_de2"}]),
    ({"en": "A"}, None, [{"en": "A"}], [{"en": "A", "de": "A_de1"}, {"en": "A", "de": "A_de2"}]),
])
def test_convert_choice_text(previous_text, expected_new_text, previous_choices, new_choices):
    data = {
        "_type": "text",
        "text": previous_text
    }
    if expected_new_text is None:
        expected_new_data = None
    else:
        expected_new_data = {
            "_type": "text",
            "text" : expected_new_text
        }
    previous_schema = {
        'type': 'text',
        'title': 'Text',
        'choices': previous_choices
    }
    new_schema = {
        'type': 'text',
        'title': 'Text',
        'choices': new_choices
    }
    validate(data, previous_schema)
    new_data, warnings = convert_to_schema(data, previous_schema, new_schema)
    assert new_data == expected_new_data
    assert bool(warnings) == (expected_new_data is None)
