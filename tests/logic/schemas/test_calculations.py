import pytest

from sampledb.logic.schemas.calculations import validate_calculation, ValidationError
from sampledb.logic.schemas.validate_schema import validate_schema


def test_validate_calculation():
    property_schemas = {
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
    }
    validate_calculation(
        {
            'property_names': ['a', 'b'],
            'digits': 2,
            'formula': 'a + b'
        },
        property_schemas,
        ['calculated_property']
    )
    validate_calculation(
        {
            'property_names': ['a', 'b'],
            'formula': 'a * b'
        },
        property_schemas,
        ['calculated_property']
    )

    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'formula': 'a * b'
            },
            property_schemas,
            ['calculated_property']
        )

    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'property_names': ['a', 'c'],
                'formula': 'a * b'
            },
            property_schemas,
            ['calculated_property']
        )

    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'property_names': ['a', 'b'],
            },
            property_schemas,
            ['calculated_property']
        )

    with pytest.raises(ValidationError):
        validate_calculation(
            [
                'property_names', 'formula'
            ],
            property_schemas,
            ['calculated_property']
        )

    property_schemas['a']['units'] = ['m', 'km']
    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'property_names': ['a', 'b'],
                'formula': 'a * b'
            },
            property_schemas,
            ['calculated_property']
        )

    property_schemas['a']['units'] = ['m']
    property_schemas['calculated_property']['units'] = ['m * s', 'km * h']
    with pytest.raises(ValidationError):
        validate_calculation(
            {
                'property_names': ['a', 'b'],
                'formula': 'a * b'
            },
            property_schemas,
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
                (schema['properties']['calculated_property']['calculation'], schema['properties'], ['calculated_property']),
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
