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
    condition_keys = set(calculation.keys())
    invalid_keys = condition_keys - valid_keys
    if invalid_keys:
        raise ValidationError(f'unexpected keys in calculation: {invalid_keys}', path)
    missing_keys = required_keys - condition_keys
    if missing_keys:
        raise ValidationError(f'missing keys in calculation: {missing_keys}', path)
    if not isinstance(calculation['property_names'], list):
        raise ValidationError('property_names must be list', path)
    if not isinstance(calculation['formula'], str):
        raise ValidationError('formula must be string', path)
    if 'digits' in calculation and not isinstance(calculation['digits'], int):
        raise ValidationError('digits must be an integer value', path)
    for property_name in calculation['property_names']:
        if property_name not in property_schemas:
            raise ValidationError('unknown property_name', path)
        if property_schemas[property_name].get('type') != 'quantity':
            raise ValidationError('property_name does not belong to a quantity property', path)
