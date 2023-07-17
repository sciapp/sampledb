import typing

from ..errors import ValidationError


def validate_calculation(
        calculation: typing.Any,
        property_schemas: typing.Dict[str, typing.Any],
        path: typing.List[str]
) -> None:
    if not isinstance(calculation, dict):
        raise ValidationError('calculation must be dict', path)
    valid_keys = {'property_names', 'formula', 'digits'}
    required_keys = {'property_names', 'formula'}
    own_property_name = path[-1]
    own_schema = property_schemas[own_property_name]
    calculation_keys = set(calculation.keys())
    invalid_keys = calculation_keys - valid_keys
    if invalid_keys:
        raise ValidationError(f'unexpected keys in calculation: {invalid_keys}', path)
    missing_keys = required_keys - calculation_keys
    if missing_keys:
        raise ValidationError(f'missing keys in calculation: {missing_keys}', path)
    if isinstance(own_schema.get('units'), list) and len(own_schema['units']) != 1:
        raise ValidationError('quantities with a calculation must have fixed units', path)
    if not isinstance(calculation['property_names'], list):
        raise ValidationError('property_names must be list', path)
    if own_property_name in calculation['property_names']:
        raise ValidationError('quantities with a calculation must not directly depend on themselves', path)
    if not isinstance(calculation['formula'], str):
        raise ValidationError('formula must be string', path)
    if 'digits' in calculation and not isinstance(calculation['digits'], int):
        raise ValidationError('digits must be an integer value', path)
    if 'digits' in calculation and not 0 <= calculation['digits'] <= 15:
        raise ValidationError('digits must be an integer value between 0 and 15', path)
    for property_name in calculation['property_names']:
        if property_name not in property_schemas:
            raise ValidationError(f'unknown property_name: {property_name}', path)
        property_schema = property_schemas[property_name]
        if property_schema.get('type') != 'quantity':
            raise ValidationError('property_name does not belong to a quantity property', path)
        if isinstance(property_schema.get('units'), list) and len(property_schema['units']) != 1:
            raise ValidationError('quantities with a calculation must only depend on quantities with fixed units', path)
