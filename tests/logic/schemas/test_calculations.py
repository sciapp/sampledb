import pytest

from sampledb.logic.schemas.calculations import validate_calculation, ValidationError, _simplify_absolute_path, _get_property_schema
from sampledb.logic.schemas.validate_schema import validate_schema


def test_validate_calculation():
    root_schema = {
        'type': 'object',
        'title': 'Test Object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'a': {
                'title': 'a',
                'type': 'quantity',
                'units': 'm'
            },
            'b': {
                'title': 'b',
                'type': 'quantity',
                'units': ['s']
            },
            'calculated_property': {
                'title': 'Calculated Property',
                'type': 'quantity',
                'units': 'm * s'
            }
        },
        'required': ['name']
    }
    validate_calculation(
        {
            'property_names': ['a', 'b'],
            'digits': 2,
            'formula': 'a + b'
        },
        root_schema,
        ['calculated_property']
    )
    validate_calculation(
        {
            'property_names': ['a', 'b'],
            'formula': 'a * b'
        },
        root_schema,
        ['calculated_property']
    )

    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'formula': 'a * b'
            },
            root_schema,
            ['calculated_property']
        )

    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'property_names': ['a', 'c'],
                'formula': 'a * b'
            },
            root_schema,
            ['calculated_property']
        )

    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'property_names': ['a', 'b'],
            },
            root_schema,
            ['calculated_property']
        )

    with pytest.raises(ValidationError):
        validate_calculation(
            [
                'property_names', 'formula'
            ],
            root_schema,
            ['calculated_property']
        )

    root_schema['properties']['a']['units'] = ['m', 'km']
    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'property_names': ['a', 'b'],
                'formula': 'a * b'
            },
            root_schema,
            ['calculated_property']
        )

    root_schema['properties']['a']['units'] = ['m']
    root_schema['properties']['calculated_property']['units'] = ['m * s', 'km * h']
    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'property_names': ['a', 'b'],
                'formula': 'a * b'
            },
            root_schema,
            ['calculated_property']
        )


def test_validate_schema_with_calculations():
    schema = {
        'title': 'Test Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'a': {
                'title': 'a',
                'type': 'quantity',
                'units': 'kg'
            },
            'b': {
                'title': 'b',
                'type': 'quantity',
                'units': 'm'
            },
            'calculated_property': {
                'title': 'Calculated Property',
                'type': 'quantity',
                'units': 'm * kg',
                'calculation': {
                    'property_names': ['a', 'b'],
                    'formula': 'a * b'
                }
            }
        },
        'required': ['name']
    }
    validate_schema(schema)
    import sampledb.logic.schemas.validate_schema

    calls = []

    def mock_validate_calculation(*args, **kwargs):
        calls.append((args, kwargs))

    try:
        sampledb.logic.schemas.calculations.validate_calculation = mock_validate_calculation
        validate_schema(schema)
        assert calls == [
            (
                (schema['properties']['calculated_property']['calculation'], schema, ['calculated_property']),
                {}
            )
        ]
    finally:
        sampledb.logic.schemas.calculations.validate_calculation = validate_calculation

    schema['properties']['calculated_property']['calculation'] = {
        'property_names': ['a', 'b'],
        'formula': 'a * b'
    }
    validate_schema(schema)

    schema['properties']['calculated_property']['units'] = ['m', 'km']
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['properties']['calculated_property']['units'] = 'm * kg'

    schema['properties']['calculated_property']['calculation'] = {
        'property_names': {'d': ['c', 0, 'd'], 'b': 'b'},
        'formula': 'd * b'
    }
    with pytest.raises(ValidationError):
        validate_schema(schema)
    schema['properties']['c'] = {
        'type': 'array',
        'title': 'c',
        'items': {
            'type': 'object',
            'title': 'o',
            'properties': {
                'd': {
                    'type': 'quantity',
                    'title': 'd',
                    'units': 'kg'
                }
            }
        }
    }
    validate_schema(schema)


def test_simplify_absolute_path():
    assert _simplify_absolute_path(['object', 'property']) == ['object', 'property']
    assert _simplify_absolute_path(['object', '..', 'object', 'property']) == ['object', 'property']
    assert _simplify_absolute_path(['object', '..', 'object', 'property', '..', 'property']) == ['object', 'property']
    assert _simplify_absolute_path(['array', '0']) == ['array', '0']
    assert _simplify_absolute_path(['array', '[?]', '..', '2']) == ['array', '2']
    assert _simplify_absolute_path(['array', '[?]', '..', '..', 'object', 'property']) == ['object', 'property']
    assert _simplify_absolute_path(['array', '+1']) == ['array', '+1']
    assert _simplify_absolute_path(['array', '-1']) == ['array', '-1']
    assert _simplify_absolute_path(['array', '[?]', '..', '..', '..']) is None


def test_get_property_schema():
    root_schema = {
        'title': 'root',
        'type': 'object',
        'properties': {
            'name': {
                'type': 'text',
                'title': 'name'
            },
            'object': {
                'title': 'object',
                'type': 'object',
                'properties': {
                    'property': {
                        'type': 'quantity',
                        'title': 'property',
                        'units': 'm'
                    }
                }
            },
            'array': {
                'title': 'array',
                'type': 'array',
                'items': {
                    'type': 'quantity',
                    'title': 'item',
                    'units': 'm'
                }
            }
        },
        'required': ['name']
    }
    assert _get_property_schema(root_schema, ['object', 'property']) == root_schema['properties']['object']['properties']['property']
    assert _get_property_schema(root_schema, ['array', '[?]']) == root_schema['properties']['array']['items']
    assert _get_property_schema(root_schema, ['array', '2']) == root_schema['properties']['array']['items']
    assert _get_property_schema(root_schema, ['array', '+1']) == root_schema['properties']['array']['items']
    assert _get_property_schema(root_schema, ['array', '-1']) == root_schema['properties']['array']['items']
    assert _get_property_schema(root_schema, ['unknown']) is None
    assert _get_property_schema(root_schema, ['array', 'items']) is None
    assert _get_property_schema(root_schema, ['object', '[?]']) is None
