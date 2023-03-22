import copy
import typing

from .. import errors


GenericDiff = typing.TypedDict('GenericDiff', {'_before': typing.Any, '_after': typing.Any}, total=False)
ArrayDiff = typing.List[typing.Optional['DataDiff']]
ObjectDiff = typing.Dict[str, typing.Optional['DataDiff']]
DataDiff = typing.Union[ArrayDiff, ObjectDiff, GenericDiff]


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
        return data.get('_type', 'object')
    return None


def _apply_array_diff(data_before: typing.List[typing.Any], data_diff: ArrayDiff) -> typing.List[typing.Any]:
    data_after = copy.deepcopy(data_before)
    for index, item_diff in enumerate(data_diff):
        value_before = data_before[index] if index < len(data_before) else VALUE_NOT_SET
        value_after = apply_diff(value_before, item_diff)
        if value_after != VALUE_NOT_SET:
            if value_before == VALUE_NOT_SET:
                data_after.append(value_after)
            else:
                data_after[index] = value_after
        elif value_before != VALUE_NOT_SET:
            del data_after[index]
    return data_after


def _apply_object_diff(data_before: typing.Dict[str, typing.Any], data_diff: ObjectDiff) -> typing.Dict[str, typing.Any]:
    data_after = copy.deepcopy(data_before)
    for property_name, property_diff in data_diff.items():
        value_before = data_before.get(property_name, VALUE_NOT_SET)
        value_after = apply_diff(value_before, property_diff)
        if value_after != VALUE_NOT_SET:
            data_after[property_name] = value_after
        elif value_before != VALUE_NOT_SET:
            del data_after[property_name]
    return data_after


def _apply_generic_diff(data_before: typing.Any, data_diff: GenericDiff) -> typing.Any:
    if '_before' in data_diff:
        if data_before != data_diff['_before']:
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


def _guess_type_of_diff(data_diff: typing.Optional[DataDiff]) -> typing.Optional[typing.Union[typing.Type[ArrayDiff], typing.Type[ObjectDiff], typing.Type[GenericDiff]]]:
    if data_diff is None:
        return None
    if isinstance(data_diff, list):
        return ArrayDiff
    assert isinstance(data_diff, dict)
    if '_before' not in data_diff and '_after' not in data_diff:
        return ObjectDiff
    return GenericDiff


def apply_diff(data_before: typing.Any, data_diff: typing.Optional[DataDiff]) -> typing.Any:
    diff_type = _guess_type_of_diff(data_diff)
    if diff_type is None:
        if data_before == VALUE_NOT_SET:
            raise errors.DiffMismatchError()
        return copy.deepcopy(data_before)
    if diff_type is ArrayDiff:
        if not isinstance(data_before, list):
            raise errors.DiffMismatchError()
        return _apply_array_diff(data_before, typing.cast(ArrayDiff, data_diff))
    if diff_type is ObjectDiff:
        if not isinstance(data_before, dict):
            raise errors.DiffMismatchError()
        return _apply_object_diff(data_before, typing.cast(ObjectDiff, data_diff))
    if diff_type is GenericDiff:
        return _apply_generic_diff(data_before, typing.cast(GenericDiff, data_diff))
    return VALUE_NOT_SET
