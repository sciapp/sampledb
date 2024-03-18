import copy
import re
import typing

from .. import errors
from ..datatypes import JSONEncoder
from .validate import validate

GenericDiff = typing.TypedDict('GenericDiff', {'_before': typing.Any, '_after': typing.Any}, total=False)
ArrayDiff = typing.List[typing.Optional['DataDiff']]
ArrayIndexDiff = typing.Dict[str, GenericDiff]
ObjectDiff = typing.Dict[str, typing.Optional['DataDiff']]
DataDiff = typing.Union[ArrayDiff, ArrayIndexDiff, ObjectDiff, GenericDiff]


class _ValueNotSet:
    pass


VALUE_NOT_SET = _ValueNotSet()


def _calculate_object_diff(data_before: typing.Dict[str, typing.Any], data_after: typing.Dict[str, typing.Any]) -> ObjectDiff:
    data_diff: ObjectDiff = {}
    for property_name in set(data_before) | set(data_after):
        value_before = data_before.get(property_name, VALUE_NOT_SET)
        value_after = data_after.get(property_name, VALUE_NOT_SET)
        value_diff = calculate_diff(value_before, value_after)
        if value_diff is not None:
            data_diff[property_name] = value_diff
    return data_diff


def _calculate_array_diff(data_before: typing.List[typing.Any], data_after: typing.List[typing.Any]) -> ArrayDiff:
    length_before = len(data_before)
    length_after = len(data_after)
    length_diff = max(length_before, length_after)
    data_diff: ArrayDiff = [None] * length_diff
    for index in range(length_diff):
        value_before = data_before[index] if index < length_before else VALUE_NOT_SET
        value_after = data_after[index] if index < length_after else VALUE_NOT_SET
        value_diff = calculate_diff(value_before, value_after)
        if value_diff is not None:
            data_diff[index] = value_diff
    return data_diff


def calculate_diff(data_before: typing.Any, data_after: typing.Any) -> typing.Optional[DataDiff]:
    if data_before == data_after:
        return None
    type_before = _guess_type_of_data(data_before)
    type_after = _guess_type_of_data(data_after)
    if type_before == type_after:
        if type_before == 'array':
            return _calculate_array_diff(data_before, data_after)
        if type_before == 'object':
            return _calculate_object_diff(data_before, data_after)
    data_diff: GenericDiff = {}
    if data_before != VALUE_NOT_SET:
        data_diff['_before'] = data_before
    if data_after != VALUE_NOT_SET:
        data_diff['_after'] = data_after
    return data_diff


def _guess_type_of_data(data: typing.Any) -> typing.Optional[str]:
    if isinstance(data, list):
        return 'array'
    if isinstance(data, dict):
        return str(data.get('_type', 'object'))
    return None


def _apply_array_diff(
        data_before: typing.List[typing.Any],
        data_diff: ArrayDiff,
        schema_before: typing.Optional[typing.Dict[str, typing.Any]]
) -> typing.List[typing.Any]:
    data_after = copy.deepcopy(data_before)
    indices_to_remove = []
    for index, item_diff in enumerate(data_diff):
        value_before = data_before[index] if index < len(data_before) else VALUE_NOT_SET
        if schema_before is None:
            item_schema_before = None
        else:
            try:
                item_schema_before = schema_before['items']
            except Exception:
                raise errors.DiffMismatchError()
        value_after = apply_diff(value_before, item_diff, item_schema_before, validate_data_before=False)
        if value_after != VALUE_NOT_SET:
            if value_before == VALUE_NOT_SET:
                data_after.append(value_after)
            else:
                data_after[index] = value_after
        elif value_before != VALUE_NOT_SET:
            indices_to_remove.append(index)
    for index in reversed(indices_to_remove):
        del data_after[index]
    return data_after


def _apply_timeseries_array_diff(
        data_before: typing.Dict[str, typing.Any],
        data_diff: ArrayDiff
) -> typing.Dict[str, typing.Any]:
    if not isinstance(data_before.get('data'), list):
        raise errors.DiffMismatchError()
    data_after = copy.deepcopy(data_before)
    data_after['data'] = _apply_array_diff(data_before=data_before['data'], data_diff=data_diff, schema_before=None)
    return data_after


def _apply_array_index_diff(
        data_before: typing.List[typing.Any],
        data_diff: ArrayIndexDiff,
        schema_before: typing.Optional[typing.Dict[str, typing.Any]]
) -> typing.List[typing.Any]:
    length_before = len(data_before)
    diffs_by_index = {}
    for index_info, item_diff in data_diff.items():
        try:
            index = int(index_info)
        except ValueError:
            raise errors.DiffMismatchError()
        if index_info.startswith('+') or index < 0:
            index += length_before
        if index < 0:
            raise errors.DiffMismatchError()
        if index in diffs_by_index:
            raise errors.DiffMismatchError()
        diffs_by_index[index] = item_diff
    new_indices = {index for index in diffs_by_index if index >= length_before}
    if new_indices:
        length_after = max(new_indices) + 1
        if new_indices != set(range(length_before, length_after)):
            raise errors.DiffMismatchError()
    else:
        length_after = length_before
    new_data_diff: ArrayDiff = [
        diffs_by_index.get(index)
        for index in range(length_after)
    ]
    return _apply_array_diff(data_before, new_data_diff, schema_before)


def _apply_timeseries_array_index_diff(
        data_before: typing.Dict[str, typing.Any],
        data_diff: ArrayIndexDiff
) -> typing.Dict[str, typing.Any]:
    if not isinstance(data_before.get('data'), list):
        raise errors.DiffMismatchError()
    data_after = copy.deepcopy(data_before)
    data_after['data'] = _apply_array_index_diff(data_before=data_before['data'], data_diff=data_diff, schema_before=None)
    return data_after


def _apply_object_diff(
        data_before: typing.Dict[str, typing.Any],
        data_diff: ObjectDiff,
        schema_before: typing.Optional[typing.Dict[str, typing.Any]]
) -> typing.Dict[str, typing.Any]:
    if schema_before is None:
        schema_before = {
            'title': '',
            'type': 'object',
            'properties': {}
        }
    data_after = copy.deepcopy(data_before)
    for property_name, property_diff in data_diff.items():
        value_before = data_before.get(property_name, VALUE_NOT_SET)
        try:
            property_schema_before = schema_before['properties'][property_name]
        except Exception:
            if isinstance(property_diff, dict) and '_after' in property_diff and '_before' not in property_diff:
                # the property did not exist before in this specific case, so an empty schema can be used
                property_schema_before = {}
            else:
                raise errors.DiffMismatchError()
        value_after = apply_diff(value_before, property_diff, property_schema_before, validate_data_before=False)
        if value_after != VALUE_NOT_SET:
            data_after[property_name] = value_after
        elif value_before != VALUE_NOT_SET:
            del data_after[property_name]
    return data_after


def _compare_generic_data(
        data_left: typing.Any,
        data_right: typing.Any
) -> bool:
    if data_left is None and data_right is None:
        return True
    if data_left == data_right:
        return True
    if isinstance(data_left, dict) and isinstance(data_right, dict):
        if '_type' in data_left and '_type' in data_right:
            if data_left['_type'] != data_right['_type']:
                return False
            try:
                value_left = JSONEncoder.serializable_types[data_left['_type']].from_json(data_left)
                value_right = JSONEncoder.serializable_types[data_right['_type']].from_json(data_right)
                return bool(value_left == value_right)
            except Exception:
                return False
        else:
            keys_left = set(data_left)
            keys_right = set(data_right)
            if keys_left != keys_right:
                return False
            return all(
                _compare_generic_data(data_left[key], data_right[key])
                for key in keys_left
            )
    if isinstance(data_left, list) and isinstance(data_right, list):
        if len(data_left) != len(data_right):
            return False
        return all(
            _compare_generic_data(item_left, item_right)
            for item_left, item_right in zip(data_left, data_right)
        )
    return False


def _apply_generic_diff(
        data_before: typing.Any,
        data_diff: GenericDiff,
        schema_before: typing.Optional[typing.Dict[str, typing.Any]]
) -> typing.Any:
    if '_before' in data_diff:
        if data_diff['_before'] is not None and schema_before is not None:
            try:
                validate(data_diff['_before'], schema_before)
            except Exception:
                raise errors.DiffMismatchError()
        if not _compare_generic_data(data_before, data_diff['_before']):
            raise errors.DiffMismatchError()
    else:
        if data_before != VALUE_NOT_SET:
            raise errors.DiffMismatchError()
    if '_after' in data_diff:
        return copy.deepcopy(data_diff['_after'])
    else:
        if data_before == VALUE_NOT_SET:
            raise errors.DiffMismatchError()
        return VALUE_NOT_SET


def _guess_type_of_diff(data_diff: typing.Optional[DataDiff]) -> typing.Optional[typing.Union[typing.Type[ArrayDiff], typing.Type[ArrayIndexDiff], typing.Type[ObjectDiff], typing.Type[GenericDiff]]]:
    if data_diff is None:
        return None
    if isinstance(data_diff, list):
        return ArrayDiff
    assert isinstance(data_diff, dict)
    if all(type(key) is str and re.match(r'^([+-]?[1-9][0-9]*)|(\+?0)$', key) for key in data_diff):
        return ArrayIndexDiff
    if '_before' not in data_diff and '_after' not in data_diff:
        return ObjectDiff
    return GenericDiff


def apply_diff(
        data_before: typing.Any,
        data_diff: typing.Optional[DataDiff],
        schema_before: typing.Optional[typing.Dict[str, typing.Any]],
        *,
        validate_data_before: bool = True
) -> typing.Any:
    if validate_data_before and schema_before is not None:
        validate(data_before, schema_before)
    diff_type = _guess_type_of_diff(data_diff)
    if diff_type is None:
        if data_before == VALUE_NOT_SET:
            raise errors.DiffMismatchError()
        return copy.deepcopy(data_before)
    if diff_type is ArrayDiff:
        if isinstance(data_before, dict) and data_before.get('_type') == 'timeseries':
            return _apply_timeseries_array_diff(data_before, typing.cast(ArrayDiff, data_diff))
        if isinstance(data_before, list):
            return _apply_array_diff(data_before, typing.cast(ArrayDiff, data_diff), schema_before)
        raise errors.DiffMismatchError()
    if diff_type is ArrayIndexDiff:
        if isinstance(data_before, dict) and data_before.get('_type') == 'timeseries':
            return _apply_timeseries_array_index_diff(data_before, typing.cast(ArrayIndexDiff, data_diff))
        if isinstance(data_before, list):
            return _apply_array_index_diff(data_before, typing.cast(ArrayIndexDiff, data_diff), schema_before)
        raise errors.DiffMismatchError()
    if diff_type is ObjectDiff:
        if not isinstance(data_before, dict):
            raise errors.DiffMismatchError()
        return _apply_object_diff(data_before, typing.cast(ObjectDiff, data_diff), schema_before)
    if diff_type is GenericDiff:
        return _apply_generic_diff(data_before, typing.cast(GenericDiff, data_diff), schema_before)
    return VALUE_NOT_SET


def invert_diff(
        data_diff: typing.Optional[DataDiff]
) -> typing.Optional[DataDiff]:
    diff_type = _guess_type_of_diff(data_diff)
    if diff_type is ArrayDiff:
        array_diff = typing.cast(ArrayDiff, data_diff)
        return [
            invert_diff(data_diff=item_diff)
            for item_diff in array_diff
        ]
    if diff_type is ArrayIndexDiff:
        array_index_diff = typing.cast(ArrayIndexDiff, data_diff)
        inverted_data_diff: ArrayIndexDiff = {}
        length_change = 0
        for item_diff in array_index_diff.values():
            if not isinstance(item_diff, dict):
                continue
            if '_after' in item_diff and '_before' not in item_diff:
                length_change += 1
            if '_before' in item_diff and '_after' not in item_diff:
                length_change -= 1
        for index_info, item_diff in array_index_diff.items():
            inverted_item_diff = typing.cast(GenericDiff, invert_diff(data_diff=item_diff))
            if index_info.startswith('+') or index_info.startswith('-'):
                try:
                    index_offset = int(index_info)
                except ValueError:
                    raise errors.DiffMismatchError()
                inverted_data_diff[f"{index_offset - length_change:+d}"] = inverted_item_diff
            else:
                inverted_data_diff[index_info] = inverted_item_diff
        return inverted_data_diff
    if diff_type is ObjectDiff:
        object_diff = typing.cast(ObjectDiff, data_diff)
        return {
            property_name: invert_diff(data_diff=property_diff)
            for property_name, property_diff in object_diff.items()
        }
    if diff_type is GenericDiff:
        generic_diff = typing.cast(GenericDiff, data_diff)
        inverted_data_diff = {}
        if '_before' in generic_diff:
            inverted_data_diff['_after'] = generic_diff['_before']
        if '_after' in generic_diff:
            inverted_data_diff['_before'] = generic_diff['_after']
        return inverted_data_diff
    return None
