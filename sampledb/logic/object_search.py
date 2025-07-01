# coding: utf-8
import functools
import itertools
import typing

from sqlalchemy import String, and_, or_
from sqlalchemy.sql.expression import select, true, false, not_
from sqlalchemy.dialects import postgresql

from . import where_filters
from . import datatypes
from . import object_search_parser
from .. import db
from ..models.objects import Objects


class Attribute:
    def __init__(
            self,
            input_text: str,
            start_position: int,
            value: typing.Any
    ) -> None:
        self.value = value
        self.input_text = input_text
        self.start_position = start_position
        self.end_position = self.start_position + len(self.input_text)


class Expression:
    def __init__(
            self,
            input_text: str,
            start_position: int,
            value: typing.Any
    ) -> None:
        self.value = value
        self.input_text = input_text
        self.start_position = start_position
        self.end_position = self.start_position + len(self.input_text)


class Reference:
    def __init__(self, value: int) -> None:
        self.value = value


unary_operator_handlers: typing.Dict[typing.Tuple[typing.Optional[type], str], typing.Callable[[typing.Any, typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]], typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]], typing.Tuple[typing.Any, typing.Any]]] = {}
binary_operator_handlers: typing.Dict[typing.Tuple[typing.Optional[type], typing.Optional[type], str], typing.Callable[[typing.Any, typing.Any, typing.Any, typing.Callable[[typing.Any], typing.Any], typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]], typing.Tuple[typing.Any, typing.Any]]] = {}


def unary_operator_handler(
        operand_type: typing.Optional[type],
        operator: str
) -> typing.Callable[[typing.Any], typing.Any]:
    def unary_operator_handler_decorator(
            func: typing.Any,
            operand_type: typing.Optional[type] = operand_type,
            operator: str = operator
    ) -> typing.Any:
        @functools.wraps(func)
        def unary_operator_handler_wrapper(
                operator: typing.Any,
                operand: typing.Any,
                outer_filter: typing.Optional[typing.Callable[[typing.Any], typing.Any]],
                search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]
        ) -> typing.Tuple[typing.Any, typing.Any]:
            input_text = operator.input_text + operand.input_text
            start_position = operator.start_position
            end_position = operand.end_position
            filter_func, outer_filter = func(operand.value, outer_filter, search_notes, input_text, start_position, end_position)
            filter_func = Expression(input_text, start_position, filter_func)
            return filter_func, outer_filter
        assert (operand_type, operator) not in unary_operator_handlers
        unary_operator_handlers[(operand_type, operator)] = unary_operator_handler_wrapper
        return unary_operator_handler_wrapper

    return unary_operator_handler_decorator


def binary_operator_handler(
        left_operand_type: typing.Optional[type],
        right_operand_type: typing.Optional[type],
        operator: str
) -> typing.Callable[[typing.Any], typing.Any]:
    def binary_operator_handler_decorator(
            func: typing.Any,
            left_operand_type: typing.Optional[type] = left_operand_type,
            right_operand_type: typing.Optional[type] = right_operand_type,
            operator: str = operator
    ) -> typing.Any:
        @functools.wraps(func)
        def binary_operator_handler_wrapper(
                left_operand: typing.Any,
                operator: typing.Any,
                right_operand: typing.Any,
                outer_filter: typing.Callable[[typing.Any], typing.Any],
                search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]
        ) -> typing.Tuple[typing.Any, typing.Any]:
            input_text = left_operand.input_text + operator.input_text + right_operand.input_text
            start_position = left_operand.start_position
            end_position = right_operand.end_position

            def null_safe_outer_filter(expr: typing.Any) -> typing.Any:
                # comparisons with null may contain null attributes, but other operations must not
                if left_operand_type == Attribute and right_operand_type != object_search_parser.Null:
                    expr = db.and_(left_operand.value != db.null(), expr)
                if right_operand_type == Attribute and left_operand_type != object_search_parser.Null:
                    expr = db.and_(right_operand.value != db.null(), expr)
                return outer_filter(expr)

            filter_func, outer_filter = func(left_operand.value, right_operand.value, null_safe_outer_filter, search_notes, input_text, start_position, end_position)
            filter_func = Expression(input_text, start_position, filter_func)
            return filter_func, outer_filter
        assert (left_operand_type, right_operand_type, operator) not in binary_operator_handlers
        binary_operator_handlers[(left_operand_type, right_operand_type, operator)] = binary_operator_handler_wrapper
        return binary_operator_handler_wrapper

    return binary_operator_handler_decorator


@unary_operator_handler(datatypes.Boolean, 'not')
def _(
        operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if not operand.value:
        search_notes.append(('warning', 'This expression will always be true', start_position, end_position))
        return outer_filter(true()), None
    else:
        search_notes.append(('warning', 'This expression will always be false', start_position, end_position))
        return outer_filter(false()), None


@unary_operator_handler(Attribute, 'not')
def _(
        operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.boolean_false(operand)), None


@unary_operator_handler(None, 'not')
def _(
        operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(not_(operand)), None


@binary_operator_handler(datatypes.Boolean, datatypes.Boolean, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.value and right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(None, None, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(and_(left_operand, right_operand)), None


@binary_operator_handler(None, datatypes.Boolean, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if right_operand.value:
        return outer_filter(left_operand), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Boolean, None, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.value:
        return outer_filter(right_operand), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(None, Attribute, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(and_(left_operand, where_filters.boolean_true(right_operand))), None


@binary_operator_handler(Attribute, None, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(and_(where_filters.boolean_true(left_operand), right_operand)), None


@binary_operator_handler(Attribute, datatypes.Boolean, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if right_operand.value:
        return outer_filter(where_filters.boolean_true(left_operand)), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Boolean, Attribute, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.value:
        return outer_filter(where_filters.boolean_true(right_operand)), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, Attribute, 'and')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(and_(where_filters.boolean_true(left_operand), where_filters.boolean_true(right_operand))), None


@binary_operator_handler(datatypes.Boolean, datatypes.Boolean, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.value or right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(None, None, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(or_(left_operand, right_operand)), None


@binary_operator_handler(None, datatypes.Boolean, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(left_operand), None


@binary_operator_handler(datatypes.Boolean, None, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(right_operand), None


@binary_operator_handler(None, Attribute, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(or_(left_operand, where_filters.boolean_true(right_operand))), None


@binary_operator_handler(Attribute, None, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(or_(where_filters.boolean_true(left_operand), right_operand)), None


@binary_operator_handler(Attribute, datatypes.Boolean, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(where_filters.boolean_true(left_operand)), None


@binary_operator_handler(datatypes.Boolean, Attribute, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(where_filters.boolean_true(right_operand)), None


@binary_operator_handler(Attribute, Attribute, 'or')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(or_(where_filters.boolean_true(left_operand), where_filters.boolean_true(right_operand))), None


@binary_operator_handler(datatypes.Boolean, datatypes.Boolean, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Text, datatypes.Text, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Boolean, datatypes.Boolean, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if not left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if not left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Text, datatypes.Text, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if not left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(true()), None
    if not left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Boolean, Attribute, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.boolean_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, object_search_parser.Null, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.attribute_not_set(left_operand)), None


@binary_operator_handler(Attribute, datatypes.Boolean, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.boolean_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Boolean, Attribute, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.boolean_equals(right_operand, not left_operand.value)), None


@binary_operator_handler(Attribute, datatypes.Boolean, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.boolean_equals(left_operand, not right_operand.value)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.DateTime, Attribute, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_equals(right_operand, left_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.Quantity, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(not_(where_filters.quantity_equals(right_operand, left_operand))), None


@binary_operator_handler(Attribute, datatypes.Quantity, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(not_(where_filters.quantity_equals(left_operand, right_operand))), None


@binary_operator_handler(datatypes.Text, Attribute, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.text_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.Text, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.text_equals(left_operand, right_operand)), None


@binary_operator_handler(Attribute, Attribute, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(left_operand == right_operand), None


@binary_operator_handler(None, None, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(left_operand == right_operand), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '<')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.utc_datetime < right_operand.utc_datetime:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '<')
def _(
        left_operand: datatypes.Quantity,
        right_operand: datatypes.Quantity,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand.magnitude_in_base_units < right_operand.magnitude_in_base_units:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, datatypes.Quantity, '<')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_less_than(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '<')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_greater_than(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '<')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_less_than(left_operand, right_operand)), None


@binary_operator_handler(datatypes.DateTime, Attribute, '<')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_greater_than(right_operand, left_operand)), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '>')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.utc_datetime > right_operand.utc_datetime:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '>')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand.magnitude_in_base_units > right_operand.magnitude_in_base_units:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, datatypes.Quantity, '>')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_greater_than(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '>')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_less_than(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '>')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_greater_than(left_operand, right_operand)), None


@binary_operator_handler(datatypes.DateTime, Attribute, '>')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_less_than_equals(right_operand, left_operand)), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '<=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.utc_datetime <= right_operand.utc_datetime:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '<=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand.magnitude_in_base_units <= right_operand.magnitude_in_base_units:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, datatypes.Quantity, '<=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_less_than_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '<=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_greater_than_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '<=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_less_than_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.DateTime, Attribute, '<=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_greater_than_equals(right_operand, left_operand)), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '>=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.utc_datetime >= right_operand.utc_datetime:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.DateTime, Attribute, '>=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_less_than_equals(right_operand, left_operand)), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '>=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand.magnitude_in_base_units >= right_operand.magnitude_in_base_units:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, datatypes.Quantity, '>=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_greater_than_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '>=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.quantity_less_than_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '>=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.datetime_greater_than_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Text, Attribute, 'in')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.text_contains(right_operand, left_operand.text)), None


@binary_operator_handler(datatypes.Text, datatypes.Text, 'in')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.text in right_operand.text:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Reference, Reference, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.value == right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, Reference, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.reference_equals(left_operand, right_operand)), None


@binary_operator_handler(Reference, Attribute, '==')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(where_filters.reference_equals(right_operand, left_operand)), None


@binary_operator_handler(Reference, Reference, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if left_operand.value != right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, Reference, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(not_(where_filters.reference_equals(left_operand, right_operand))), None


@binary_operator_handler(Reference, Attribute, '!=')
def _(
        left_operand: typing.Any,
        right_operand: typing.Any,
        outer_filter: typing.Callable[[typing.Any], typing.Any],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        input_text: str,
        start_position: int,
        end_position: int
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    return outer_filter(not_(where_filters.reference_equals(right_operand, left_operand))), None


def transform_literal_to_query(
        db_obj: typing.Any,
        literal: object_search_parser.Literal,
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        use_permissions_filter_for_referenced_objects: bool,
        subquery_id_generator: typing.Iterator[int]
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if isinstance(literal, object_search_parser.Tag):
        return Expression(literal.input_text, literal.start_position, where_filters.tags_contain(db_obj[('tags',)], literal.value)), None

    if isinstance(literal, object_search_parser.Attribute):
        attributes = literal.value
        outer_filter_stack = []
        for attribute in attributes:
            follow_object_reference = attribute.startswith('*')
            if follow_object_reference:
                attribute = attribute[1:]
            if attribute == '?':
                subquery_id = next(subquery_id_generator)
                outer_filter_stack.append(
                    functools.partial(
                        lambda filter, db_obj, subquery_id: (
                            db.and_(
                                db.func.jsonb_typeof(db_obj) == 'array',
                                select(
                                    1
                                ).select_from(
                                    select(
                                        db.literal_column('value').label(f'array_{subquery_id}_data')
                                    ).select_from(
                                        db.func.jsonb_array_elements(db_obj)
                                    ).subquery()
                                ).filter(
                                    filter
                                ).exists()
                            )
                        ),
                        db_obj=db_obj,
                        subquery_id=subquery_id,
                    )
                )
                db_obj = db.literal_column(f'array_{subquery_id}_data').cast(postgresql.JSONB)
            else:
                try:
                    attribute = int(attribute)
                except ValueError:
                    pass
                db_obj = db_obj[attribute]
            if follow_object_reference:
                subquery_id = next(subquery_id_generator)
                if use_permissions_filter_for_referenced_objects:
                    permissions_filter = select(
                        1
                    ).select_from(
                        db.text('user_object_permissions_by_all')
                    ).where(
                        db.and_(
                            db.literal_column('user_object_permissions_by_all.object_id') == db.literal_column(f'referenced_object_{subquery_id}_id'),
                            db.or_(
                                db.literal_column('user_object_permissions_by_all.user_id') == db.text(':user_id'),
                                db.literal_column('user_object_permissions_by_all.user_id') == db.null()
                            ),
                            db.or_(
                                db.literal_column('user_object_permissions_by_all.requires_anonymous_users') == db.false(),
                                db.text(':enable_anonymous_users') == db.true()
                            ),
                            db.or_(
                                db.literal_column('user_object_permissions_by_all.requires_instruments') == db.false(),
                                db.text(':enable_instruments') == db.true()
                            )
                        )
                    ).having(
                        db.func.max(db.literal_column('user_object_permissions_by_all.permissions_int')) > 0
                    ).exists()
                else:
                    permissions_filter = db.true()
                outer_filter_stack.append(
                    functools.partial(
                        lambda filter, db_obj, subquery_id, permissions_filter: (
                            db.and_(
                                db.or_(
                                    db_obj['_type'].astext == 'object_reference',
                                    db_obj['_type'].astext == 'measurement',
                                    db_obj['_type'].astext == 'sample'
                                ),
                                select(
                                    1
                                ).select_from(
                                    select(
                                        Objects.object_id_column.label(f'referenced_object_{subquery_id}_id'),
                                        Objects.data_column.label(f'referenced_object_{subquery_id}_data')
                                    ).subquery()
                                ).filter(
                                    db.and_(
                                        db_obj['object_id'].cast(db.Integer) == db.literal_column(f'referenced_object_{subquery_id}_id'),
                                        permissions_filter,
                                        filter
                                    )
                                ).exists()
                            )
                        ),
                        db_obj=db_obj,
                        subquery_id=subquery_id,
                        permissions_filter=permissions_filter,
                    )
                )
                db_obj = db.literal_column(f'referenced_object_{subquery_id}_data').cast(postgresql.JSONB)
        outer_filter: typing.Optional[typing.Callable[[typing.Any], typing.Any]]
        if outer_filter_stack:
            def outer_filter(filter: typing.Any) -> typing.Any:
                for partial_outer_filter in outer_filter_stack[::-1]:
                    filter = partial_outer_filter(filter)
                return filter
        else:
            outer_filter = None
        return Attribute(literal.input_text, literal.start_position, db_obj), outer_filter

    if isinstance(literal, object_search_parser.Null):
        return literal, None

    if isinstance(literal, object_search_parser.Boolean):
        return literal, None

    if isinstance(literal, object_search_parser.Date):
        return literal, None

    if isinstance(literal, object_search_parser.Quantity):
        return literal, None

    if isinstance(literal, object_search_parser.Text):
        return literal, None

    if isinstance(literal, object_search_parser.Reference):
        return literal, None

    search_notes.append(('error', "Invalid search query", 0, None))
    return false(), None


def transform_unary_operation_to_query(
        db_obj: typing.Any,
        operator: object_search_parser.Operator,
        operand: typing.Union[Attribute, Expression, object_search_parser.Literal, typing.List[typing.Any]],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        use_permissions_filter_for_referenced_objects: bool,
        subquery_id_generator: typing.Iterator[int]
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    start_token = operator
    start = start_token.start_position
    end_token = operand
    while isinstance(end_token, list):
        end_token = end_token[0]
    end = end_token.start_position + len(end_token.input_text)
    operand_query, outer_filter = transform_tree_to_query(db_obj, operand, search_notes, use_permissions_filter_for_referenced_objects, subquery_id_generator)
    if not outer_filter:
        def outer_filter(filter: typing.Any) -> typing.Any:
            return filter

    str_operator = operator.operator
    operator_aliases = {
        '!': 'not'
    }
    str_operator = operator_aliases.get(str_operator, str_operator)

    operand_type: typing.Optional[type]
    if isinstance(operand_query, object_search_parser.Boolean):
        operand_type = datatypes.Boolean
    elif isinstance(operand_query, object_search_parser.Date):
        operand_type = datatypes.DateTime
    elif isinstance(operand_query, object_search_parser.Quantity):
        operand_type = datatypes.Quantity
    elif isinstance(operand_query, object_search_parser.Text):
        operand_type = datatypes.Text
    elif isinstance(operand_query, object_search_parser.Reference):
        operand_type = Reference
    elif isinstance(operand_query, Attribute):
        operand_type = Attribute
    else:
        operand_type = None

    if (operand_type, str_operator) in unary_operator_handlers:
        return unary_operator_handlers[(operand_type, str_operator)](operator, operand_query, outer_filter, search_notes)

    search_notes.append(('error', "Unknown unary operation", start, end))
    if hasattr(operand, 'input_text'):
        return Expression(operator.input_text + operand_query.input_text, operator.start_position, false()), None
    return false(), None


def transform_binary_operation_to_query(
        db_obj: typing.Any,
        left_operand: typing.Union[Attribute, Expression, object_search_parser.Literal, typing.List[typing.Any]],
        operator: object_search_parser.Operator,
        right_operand: typing.Union[Attribute, Expression, object_search_parser.Literal, typing.List[typing.Any]],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        use_permissions_filter_for_referenced_objects: bool,
        subquery_id_generator: typing.Iterator[int]
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    start_token = left_operand
    while isinstance(start_token, list):
        start_token = start_token[0]
    start = start_token.start_position
    end_token = right_operand
    while isinstance(end_token, list):
        end_token = end_token[-1]
    end = end_token.start_position + len(end_token.input_text)

    left_operand, left_outer_filter = transform_tree_to_query(db_obj, left_operand, search_notes, use_permissions_filter_for_referenced_objects, subquery_id_generator)
    right_operand, right_outer_filter = transform_tree_to_query(db_obj, right_operand, search_notes, use_permissions_filter_for_referenced_objects, subquery_id_generator)

    if left_outer_filter and right_outer_filter:
        search_notes.append(('error', "Multiple array placeholders", start, end))
        if hasattr(left_operand, 'input_text') and hasattr(left_operand, 'start_position') and hasattr(right_operand, 'input_text'):
            return Expression(left_operand.input_text + operator.input_text + right_operand.input_text, left_operand.start_position, false()), None
        return false(), None
    if left_outer_filter:
        outer_filter = left_outer_filter
    elif right_outer_filter:
        outer_filter = right_outer_filter
    else:
        def outer_filter(filter: typing.Any) -> typing.Any:
            return filter

    str_operator = operator.operator
    operator_aliases = {
        '||': 'or',
        '&&': 'and',
        '=': '=='
    }
    str_operator = operator_aliases.get(str_operator, str_operator)

    left_operand_type: typing.Optional[type]
    if isinstance(left_operand, object_search_parser.Boolean):
        left_operand_type = datatypes.Boolean
    elif isinstance(left_operand, object_search_parser.Date):
        left_operand_type = datatypes.DateTime
    elif isinstance(left_operand, object_search_parser.Quantity):
        left_operand_type = datatypes.Quantity
    elif isinstance(left_operand, object_search_parser.Text):
        left_operand_type = datatypes.Text
    elif isinstance(left_operand, object_search_parser.Reference):
        left_operand_type = Reference
    elif isinstance(left_operand, Attribute):
        left_operand_type = Attribute
    elif isinstance(left_operand, object_search_parser.Null):
        left_operand_type = object_search_parser.Null
    else:
        left_operand_type = None

    right_operand_type: typing.Optional[type]
    if isinstance(right_operand, object_search_parser.Boolean):
        right_operand_type = datatypes.Boolean
    elif isinstance(right_operand, object_search_parser.Date):
        right_operand_type = datatypes.DateTime
    elif isinstance(right_operand, object_search_parser.Quantity):
        right_operand_type = datatypes.Quantity
    elif isinstance(right_operand, object_search_parser.Text):
        right_operand_type = datatypes.Text
    elif isinstance(right_operand, object_search_parser.Reference):
        right_operand_type = Reference
    elif isinstance(right_operand, Attribute):
        right_operand_type = Attribute
    elif isinstance(right_operand, object_search_parser.Null):
        right_operand_type = object_search_parser.Null
    else:
        right_operand_type = None

    if datatypes.DateTime in (left_operand_type, right_operand_type):
        if str_operator.strip() == 'after':
            str_operator = '>'
        elif str_operator.strip() == 'before':
            str_operator = '<'
        elif str_operator.strip() == 'on':
            str_operator = '=='

    if (left_operand_type, right_operand_type, str_operator) in binary_operator_handlers:
        expression, outer_filter = binary_operator_handlers[(left_operand_type, right_operand_type, str_operator)](left_operand, operator, right_operand, outer_filter, search_notes)
        if str_operator.strip() in ('in', '==') and isinstance(left_operand, object_search_parser.Text) and isinstance(right_operand, Attribute) and right_operand.input_text.strip() == 'file_name':
            if str_operator.strip() == 'in':
                expression.value = db.or_(
                    where_filters.file_name_contains(db_obj, left_operand.value),
                    expression.value
                )
            else:
                expression.value = db.or_(
                    where_filters.file_name_equals(db_obj, left_operand.value),
                    expression.value
                )
        if str_operator.strip() == '==' and isinstance(right_operand, object_search_parser.Text) and isinstance(left_operand, Attribute) and left_operand.input_text.strip() == 'file_name':
            expression.value = db.or_(
                where_filters.file_name_equals(db_obj, right_operand.value),
                expression.value
            )
        return expression, outer_filter

    search_notes.append(('error', "Unknown binary operation", start, end))
    if hasattr(left_operand, 'start_position') and hasattr(left_operand, 'input_text') and hasattr(right_operand, 'input_text'):
        return Expression(left_operand.input_text + operator.input_text + right_operand.input_text, left_operand.start_position, false()), None
    return false(), None


def transform_tree_to_query(
        db_obj: typing.Any,
        tree: typing.Union[Attribute, Expression, object_search_parser.Operator, object_search_parser.Literal, typing.List[typing.Any]],
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
        use_permissions_filter_for_referenced_objects: bool,
        subquery_id_generator: typing.Optional[typing.Iterator[int]] = None
) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable[[typing.Any], typing.Any]]]:
    if subquery_id_generator is None:
        subquery_id_generator = itertools.count(1)
    if isinstance(tree, object_search_parser.Literal):
        return transform_literal_to_query(db_obj, tree, search_notes, use_permissions_filter_for_referenced_objects, subquery_id_generator)
    if not isinstance(tree, list):
        search_notes.append(('error', "Invalid search query", 0, None))
        return false(), None
    if len(tree) == 1:
        value, = tree
        return transform_tree_to_query(db_obj, value, search_notes, use_permissions_filter_for_referenced_objects)
    if len(tree) == 2:
        if isinstance(tree[0], object_search_parser.Attribute) and tree[0].is_partial_attribute and isinstance(tree[1], list):
            partial_attribute, subtree = tree
            partial_attribute_transformed, partial_attribute_outer_filter = transform_literal_to_query(db_obj, partial_attribute, search_notes, use_permissions_filter_for_referenced_objects, subquery_id_generator)
            print(partial_attribute_transformed)
            filter_func, outer_filter = transform_tree_to_query(partial_attribute_transformed.value, subtree, search_notes, use_permissions_filter_for_referenced_objects, subquery_id_generator)
            if outer_filter is None:
                outer_filter = partial_attribute_outer_filter
            if partial_attribute_outer_filter is not None and outer_filter is not None:
                outer_filter = functools.partial(
                    lambda filter, outer_filter1, outer_filter2: outer_filter2(outer_filter1(filter)),
                    outer_filter1=outer_filter,
                    outer_filter2=partial_attribute_outer_filter
                )
            return filter_func, outer_filter
        operator, operand = tree
        if isinstance(operator, object_search_parser.Operator):
            return transform_unary_operation_to_query(db_obj, operator, operand, search_notes, use_permissions_filter_for_referenced_objects, subquery_id_generator)
        search_notes.append(('error', "Invalid search query (missing operator)", 0, None))
        return false(), None
    if len(tree) == 3:
        left_operand, operator, right_operand = tree
        if isinstance(operator, object_search_parser.Operator):
            return transform_binary_operation_to_query(db_obj, left_operand, operator, right_operand, search_notes, use_permissions_filter_for_referenced_objects, subquery_id_generator)
        search_notes.append(('error', "Invalid search query (missing operator)", 0, None))
        return false(), None
    search_notes.append(('error', "Invalid search query", 0, None))
    return false(), None


def should_use_advanced_search(
        query_string: str
) -> typing.Tuple[bool, str]:
    """
    Detect whether the advanced search should be used automatically.

    The user can force the use of the advanced search, but for specific search
    query strings, the advanced search will be more appropriate, e.g. when
    the user tries to use comparisons or search for tags.

    To prevent an automatic advanced search, users can quote their query
    strings. This way they will use the simple, text-based search.

    :param query_string: the original query string
    :return: whether to use the advanced search and a modified query string
    """
    if query_string[0] == query_string[-1] == '"':
        # Remove quotes around the query string
        return False, query_string[1:-1]

    for operator in ('=', '<', '>', '#', '&', '|'):
        if operator in query_string:
            return True, query_string

    return False, query_string


def generate_filter_func(
        query_string: str,
        use_advanced_search: bool,
        use_permissions_filter_for_referenced_objects: bool = False
) -> typing.Tuple[typing.Callable[[typing.Any, typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]], typing.Any], typing.Any, bool]:
    """
    Generates a filter function for use with SQLAlchemy and the JSONB data
    attribute in the object tables.

    The generated filter functions can be used for objects.get_objects() if
    use_permissions_filter_for_referenced_objects is False, or with
    object_permissions.get_objects_with_permissions() otherwise.

    :param query_string: the query string
    :param use_advanced_search: whether to use simple text search (False) or advanced search (True)
    :param use_permissions_filter_for_referenced_objects: whether to apply a
        permissions filter when searching via object references
    :return: filter func, search tree and whether the advanced search was used
    """
    filter_func: typing.Callable[[typing.Any, typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]], typing.Any]
    tree = None
    query_string = query_string.strip()
    if query_string:
        if not use_advanced_search:
            use_advanced_search, query_string = should_use_advanced_search(query_string)
        if use_advanced_search:
            # Advanced search using parser and where_filters
            try:
                tree = object_search_parser.parse_query_string(query_string)
            except object_search_parser.ParseError as e:
                def filter_func(
                        data: typing.Any,
                        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
                        e: object_search_parser.ParseError = e
                ) -> typing.Any:
                    """ Return no objects and set search_notes"""
                    search_notes.append(('error', e.message, e.start, e.end))
                    return False
                return filter_func, None, use_advanced_search
            except Exception:
                def filter_func(
                        data: typing.Any,
                        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
                        start: int = 0,
                        end: int = len(query_string)
                ) -> typing.Any:
                    """ Return no objects and set search_notes"""
                    search_notes.append(('error', "Failed to parse query string", start, end))
                    return False
                return filter_func, None, use_advanced_search
            if isinstance(tree, list) and not tree:
                def filter_func(  # pylint: disable=function-redefined
                        data: typing.Any,
                        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
                        start: int = 0,
                        end: int = len(query_string)
                ) -> typing.Any:
                    """ Return no objects and set search_notes"""
                    search_notes.append(('error', 'Empty search', start, end))
                    return False
                return filter_func, None, use_advanced_search
            if isinstance(tree, object_search_parser.Literal):
                if isinstance(tree, object_search_parser.Boolean):
                    if tree.value.value:
                        def filter_func(  # pylint: disable=function-redefined
                                data: typing.Any,
                                search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
                                start: int = 0,
                                end: int = len(query_string)
                        ) -> typing.Any:
                            """ Return all objects and set search_notes"""
                            search_notes.append(('warning', 'This search will always return all objects', start, end))
                            return True
                        return filter_func, tree, use_advanced_search
                    else:
                        def filter_func(  # pylint: disable=function-redefined
                                data: typing.Any,
                                search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
                                start: int = 0,
                                end: int = len(query_string)
                        ) -> typing.Any:
                            """ Return no objects and set search_notes"""
                            search_notes.append(('warning', 'This search will never return any objects', start, end))
                            return False
                        return filter_func, tree, use_advanced_search
                elif isinstance(tree, object_search_parser.Attribute):
                    pass
                elif isinstance(tree, object_search_parser.Tag):
                    pass
                else:
                    def filter_func(  # pylint: disable=function-redefined
                            data: typing.Any,
                            search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
                            start: int = 0,
                            end: int = len(query_string)
                    ) -> typing.Any:
                        """ Return no objects and set search_notes"""
                        search_notes.append(('error', 'Unable to use literal as search query', start, end))
                        return False
                    return filter_func, None, use_advanced_search

            def filter_func(  # pylint: disable=function-redefined
                    data: typing.Any,
                    search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
                    tree: typing.Any = tree
            ) -> typing.Any:
                """ Filter objects based on search query string """

                data_name = str(data).split('.', maxsplit=1)[-1]  # "data" or "data_full", depending on the column name used
                db_obj = db.literal_column(data_name).cast(postgresql.JSONB)
                filter_func, outer_filter = transform_tree_to_query(db_obj, tree, search_notes, use_permissions_filter_for_referenced_objects)
                # check bool if filter_func is only an attribute
                if isinstance(filter_func, Expression):
                    filter_func = filter_func.value
                if isinstance(filter_func, Attribute):
                    filter_func = where_filters.boolean_true(filter_func.value)
                if outer_filter:
                    filter_func = outer_filter(filter_func)
                return filter_func
        else:
            # Simple search in values
            def filter_func(
                    data: typing.Any,
                    search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]],
                    query_string: str = query_string
            ) -> typing.Any:
                """ Filter objects based on search query string """
                # escape /, % and _ as that is required for ILIKE
                query_string = query_string.replace('\\', '\\\\')
                query_string = query_string.replace('%', '\\%')
                query_string = query_string.replace('_', '\\_')
                # escape " as that will have happened during JSON serialization in PostgreSQL
                query_string = query_string.replace('"', '\\\\"')
                return data.cast(String).ilike('%: "%' + query_string + '%"%', escape='\\')
    else:
        def filter_func(
                data: typing.Any,
                search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]
        ) -> typing.Any:
            """ Return all objects"""
            return True
    return filter_func, tree, use_advanced_search


def wrap_filter_func(
        filter_func: typing.Callable[[typing.Any, typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]], typing.Any]
) -> typing.Tuple[typing.Callable[[typing.Any], typing.Any], typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]]:
    """
    Wrap a filter function so that a new list will be filled with the search notes.

    :param filter_func: the filter function to wrap
    :return: the wrapped filter function and the search notes list
    """
    search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]] = []

    def wrapped_filter_func(  # pylint: disable=dangerous-default-value
            *args: typing.Any,
            search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]] = search_notes,
            filter_func_impl: typing.Any = filter_func,
            **kwargs: typing.Any
    ) -> typing.Any:
        return filter_func_impl(*args, search_notes=search_notes, **kwargs)

    return wrapped_filter_func, search_notes
