import typing
import re
import string

from ..errors import ValidationError
from .utils import schema_iter


def _get_property_schema(
        root_schema: typing.Dict[str, typing.Any],
        absolute_path: typing.List[str]
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    filter_property_path = tuple(
        path_element if isinstance(path_element, str) and path_element not in ('[?]', '*') and not re.match(r'^[-+]?[0-9]+$', path_element) else None
        for path_element in absolute_path
    )
    return dict(schema_iter(
        root_schema,
        filter_path_depth_limit=len(filter_property_path),
        filter_property_path=filter_property_path,
    )).get(filter_property_path)


def _simplify_absolute_path(
    absolute_path: typing.List[str]
) -> typing.Optional[typing.List[str]]:
    simplified_path: typing.List[str] = []
    for path_element in absolute_path:
        if path_element == '..':
            if not simplified_path:
                return None
            simplified_path.pop()
        else:
            simplified_path.append(path_element)
    return simplified_path


def validate_calculation(
        calculation: typing.Any,
        root_schema: typing.Dict[str, typing.Any],
        path: typing.List[str]
) -> None:
    if not isinstance(calculation, dict):
        raise ValidationError('calculation must be dict', path)
    valid_keys = {'property_names', 'formula', 'digits'}
    required_keys = {'property_names', 'formula'}
    calculation_keys = set(calculation.keys())
    invalid_keys = calculation_keys - valid_keys
    if invalid_keys:
        raise ValidationError(f'unexpected keys in calculation: {invalid_keys}', path)
    missing_keys = required_keys - calculation_keys
    if missing_keys:
        raise ValidationError(f'missing keys in calculation: {missing_keys}', path)
    own_schema = _get_property_schema(root_schema, path)
    if own_schema is None:
        raise ValidationError('internal schema validation error', path)
    if isinstance(own_schema.get('units'), list) and len(own_schema['units']) != 1:
        raise ValidationError('quantities with a calculation must have fixed units', path)
    if not isinstance(calculation['property_names'], dict):
        if not isinstance(calculation['property_names'], list):
            raise ValidationError('property_names must be dict or list', path)
        property_names = {
            property_name: property_name
            for property_name in calculation['property_names']
        }
    else:
        property_names = calculation['property_names']
    if not isinstance(calculation['formula'], str):
        raise ValidationError('formula must be string', path)
    if 'digits' in calculation and not isinstance(calculation['digits'], int):
        raise ValidationError('digits must be an integer value', path)
    if 'digits' in calculation and not 0 <= calculation['digits'] <= 15:
        raise ValidationError('digits must be an integer value between 0 and 15', path)
    for property_alias, relative_property_path in property_names.items():
        if isinstance(relative_property_path, str):
            relative_property_path = [relative_property_path]
        if not isinstance(property_alias, str) or '__' in property_alias or not all(c in (string.ascii_letters + string.digits + '_') for c in property_alias) or property_alias[0] not in string.ascii_letters or property_alias.endswith('_'):
            raise ValidationError('invalid property alias: ' + str(property_alias), path)
        if not all(type(path_element) in [str, int] for path_element in relative_property_path):
            raise ValidationError('expected list of strings and/or integers, but got: ' + str(relative_property_path), path)
        if '[?]' in relative_property_path:
            raise ValidationError('invalid property path: ' + str(relative_property_path), path)
        absolute_property_path = _simplify_absolute_path(path[:-1] + relative_property_path)
        if absolute_property_path is None:
            raise ValidationError('invalid property path: ' + str(relative_property_path), path)
        if path == absolute_property_path:
            # this will not cover all possible instances of self-referential
            # quantities due to array complexities, so those need to be
            # handled in javascript
            raise ValidationError('quantities with a calculation must not directly depend on themselves', path)
        property_schema = _get_property_schema(root_schema, absolute_property_path)
        if property_schema is None:
            raise ValidationError('invalid property path: ' + str(relative_property_path), path)
        if property_schema.get('type') != 'quantity':
            raise ValidationError('property_name does not belong to a quantity property', path)
        if isinstance(property_schema.get('units'), list) and len(property_schema['units']) != 1:
            raise ValidationError('quantities with a calculation must only depend on quantities with fixed units', path)
