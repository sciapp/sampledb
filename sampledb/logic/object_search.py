# coding: utf-8
import functools
import json
import typing
from sqlalchemy import String, and_, or_
from sqlalchemy.sql.expression import select, true, false, not_
from . import where_filters
from . import datatypes
from . import object_search_parser
from .. import db
import sqlalchemy.dialects.postgresql as postgresql


class Attribute:
    def __init__(self, input_text: str, start_position: int, value):
        self.value = value
        self.input_text = input_text
        self.start_position = start_position
        self.end_position = self.start_position + len(self.input_text)


class Expression:
    def __init__(self, input_text: str, start_position: int, value):
        self.value = value
        self.input_text = input_text
        self.start_position = start_position
        self.end_position = self.start_position + len(self.input_text)


unary_operator_handlers = {}
binary_operator_handlers = {}


def unary_operator_handler(operand_type, operator):
    def unary_operator_handler_decorator(func, operand_type=operand_type, operator=operator):
        @functools.wraps(func)
        def unary_operator_handler_wrapper(operator, operand, outer_filter, search_notes):
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


def binary_operator_handler(left_operand_type, right_operand_type, operator):
    def binary_operator_handler_decorator(func, left_operand_type=left_operand_type, right_operand_type=right_operand_type, operator=operator):
        @functools.wraps(func)
        def binary_operator_handler_wrapper(left_operand, operator, right_operand, outer_filter, search_notes):
            input_text = left_operand.input_text + operator.input_text + right_operand.input_text
            start_position = left_operand.start_position
            end_position = right_operand.end_position
            filter_func, outer_filter = func(left_operand.value, right_operand.value, outer_filter, search_notes, input_text, start_position, end_position)
            filter_func = Expression(input_text, start_position, filter_func)
            return filter_func, outer_filter
        assert (left_operand_type, right_operand_type, operator) not in binary_operator_handlers
        binary_operator_handlers[(left_operand_type, right_operand_type, operator)] = binary_operator_handler_wrapper
        return binary_operator_handler_wrapper

    return binary_operator_handler_decorator


@unary_operator_handler(datatypes.Boolean, 'not')
def _(operand, outer_filter, search_notes, input_text, start_position, end_position):
    if not operand.value:
        search_notes.append(('warning', 'This expression will always be true', start_position, end_position))
        return outer_filter(true()), None
    else:
        search_notes.append(('warning', 'This expression will always be false', start_position, end_position))
        return outer_filter(false()), None


@unary_operator_handler(Attribute, 'not')
def _(operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.boolean_false(operand)), None


@unary_operator_handler(None, 'not')
def _(operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(not_(operand)), None


@binary_operator_handler(datatypes.Boolean, datatypes.Boolean, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.value and right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(None, None, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(and_(left_operand, right_operand)), None


@binary_operator_handler(None, datatypes.Boolean, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if right_operand.value:
        return outer_filter(left_operand), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Boolean, None, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.value:
        return outer_filter(right_operand), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(None, Attribute, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(and_(left_operand, where_filters.boolean_true(right_operand))), None


@binary_operator_handler(Attribute, None, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(and_(where_filters.boolean_true(left_operand), right_operand)), None


@binary_operator_handler(Attribute, datatypes.Boolean, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if right_operand.value:
        return outer_filter(where_filters.boolean_true(left_operand)), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Boolean, Attribute, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.value:
        return outer_filter(where_filters.boolean_true(right_operand)), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, Attribute, 'and')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(and_(where_filters.boolean_true(left_operand), where_filters.boolean_true(right_operand))), None


@binary_operator_handler(datatypes.Boolean, datatypes.Boolean, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.value or right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(None, None, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(or_(left_operand, right_operand)), None


@binary_operator_handler(None, datatypes.Boolean, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(left_operand), None


@binary_operator_handler(datatypes.Boolean, None, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(right_operand), None


@binary_operator_handler(None, Attribute, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(or_(left_operand, where_filters.boolean_true(right_operand))), None


@binary_operator_handler(Attribute, None, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(or_(where_filters.boolean_true(left_operand), right_operand)), None


@binary_operator_handler(Attribute, datatypes.Boolean, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(where_filters.boolean_true(left_operand)), None


@binary_operator_handler(datatypes.Boolean, Attribute, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(where_filters.boolean_true(right_operand)), None


@binary_operator_handler(Attribute, Attribute, 'or')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(or_(where_filters.boolean_true(left_operand), where_filters.boolean_true(right_operand))), None


@binary_operator_handler(datatypes.Boolean, datatypes.Boolean, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Text, datatypes.Text, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand == right_operand:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Boolean, datatypes.Boolean, '!=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if not (left_operand == right_operand):
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '!=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if not (left_operand == right_operand):
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Text, datatypes.Text, '!=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if not (left_operand == right_operand):
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '!=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(true()), None
    if not (left_operand == right_operand):
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Boolean, Attribute, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.boolean_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.Boolean, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.boolean_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Boolean, Attribute, '!=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.boolean_equals(right_operand, not left_operand.value)), None


@binary_operator_handler(Attribute, datatypes.Boolean, '!=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.boolean_equals(left_operand, not right_operand.value)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.DateTime, Attribute, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_equals(right_operand, left_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.Quantity, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '!=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(not_(where_filters.quantity_equals(right_operand, left_operand))), None


@binary_operator_handler(Attribute, datatypes.Quantity, '!=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(not_(where_filters.quantity_equals(left_operand, right_operand))), None


@binary_operator_handler(datatypes.Text, Attribute, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.text_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.Text, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.text_equals(left_operand, right_operand)), None


@binary_operator_handler(Attribute, Attribute, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(left_operand == right_operand), None


@binary_operator_handler(None, None, '==')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(left_operand == right_operand), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '<')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.utc_datetime < right_operand.utc_datetime:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '<')
def _(left_operand: datatypes.Quantity, right_operand: datatypes.Quantity, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand.magnitude_in_base_units < right_operand.magnitude_in_base_units:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, datatypes.Quantity, '<')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_less_than(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '<')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_greater_than(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '<')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_less_than(left_operand, right_operand)), None


@binary_operator_handler(datatypes.DateTime, Attribute, '<')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_greater_than(right_operand, left_operand)), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '>')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.utc_datetime > right_operand.utc_datetime:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '>')
def _(left_operand: datatypes.Quantity, right_operand: datatypes.Quantity, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand.magnitude_in_base_units > right_operand.magnitude_in_base_units:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, datatypes.Quantity, '>')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_greater_than(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '>')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_less_than(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '>')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_greater_than(left_operand, right_operand)), None


@binary_operator_handler(datatypes.DateTime, Attribute, '>')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_less_than_equals(right_operand, left_operand)), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '<=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.utc_datetime <= right_operand.utc_datetime:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '<=')
def _(left_operand: datatypes.Quantity, right_operand: datatypes.Quantity, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand.magnitude_in_base_units <= right_operand.magnitude_in_base_units:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, datatypes.Quantity, '<=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_less_than_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '<=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_greater_than_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '<=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_less_than_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.DateTime, Attribute, '<=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_greater_than_equals(right_operand, left_operand)), None


@binary_operator_handler(datatypes.DateTime, datatypes.DateTime, '>=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.utc_datetime >= right_operand.utc_datetime:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(datatypes.DateTime, Attribute, '>=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_less_than_equals(right_operand, left_operand)), None


@binary_operator_handler(datatypes.Quantity, datatypes.Quantity, '>=')
def _(left_operand: datatypes.Quantity, right_operand: datatypes.Quantity, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.dimensionality != right_operand.dimensionality:
        search_notes.append(('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None))
        return outer_filter(false()), None
    if left_operand.magnitude_in_base_units >= right_operand.magnitude_in_base_units:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


@binary_operator_handler(Attribute, datatypes.Quantity, '>=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_greater_than_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Quantity, Attribute, '>=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.quantity_less_than_equals(right_operand, left_operand)), None


@binary_operator_handler(Attribute, datatypes.DateTime, '>=')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.datetime_greater_than_equals(left_operand, right_operand)), None


@binary_operator_handler(datatypes.Text, Attribute, 'in')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    return outer_filter(where_filters.text_contains(right_operand, left_operand.text)), None


@binary_operator_handler(datatypes.Text, datatypes.Text, 'in')
def _(left_operand, right_operand, outer_filter, search_notes, input_text, start_position, end_position):
    if left_operand.text in right_operand.text:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None


def transform_literal_to_query(data, literal: object_search_parser.Literal, search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]) -> typing.Tuple[typing.Any, typing.Optional[typing.Callable]]:
    if isinstance(literal, object_search_parser.Tag):
        return Expression(literal.input_text, literal.start_position, where_filters.tags_contain(data[('tags',)], literal.value)), None

    if isinstance(literal, object_search_parser.Attribute):
        attributes = literal.value
        # covert any numeric arguments to integers (array indices)
        for i, attribute in enumerate(attributes):
            try:
                attributes[i] = int(attribute)
            except ValueError:
                pass
        if '?' in attributes:
            array_placeholder_index = attributes.index('?')
            # no danger of SQL injection as attributes may only consist of
            # characters and underscores at this point
            jsonb_selector = ''
            for i, attribute in enumerate(attributes[:array_placeholder_index]):
                if isinstance(attribute, int):
                    attribute = str(attribute)
                else:
                    attribute = "'" + attribute + "'"
                if i > 0:
                    jsonb_selector += " -> "
                jsonb_selector += attribute
            array_items = select(columns=[db.text('value FROM jsonb_array_elements_text((data -> {0})::jsonb)'.format(jsonb_selector))])
            db_obj = db.literal_column('value').cast(postgresql.JSONB)
            for attribute in attributes[array_placeholder_index + 1:]:
                db_obj = db_obj[attribute]
            return Attribute(literal.input_text, literal.start_position, db_obj), lambda filter: array_items.filter(db.and_(db.text('jsonb_typeof(data -> {0}) = \'array\''.format(jsonb_selector)), filter)).exists()
        return Attribute(literal.input_text, literal.start_position, data[attributes]), None

    if isinstance(literal, object_search_parser.Boolean):
        return literal, None

    if isinstance(literal, object_search_parser.Date):
        return literal, None

    if isinstance(literal, object_search_parser.Quantity):
        return literal, None

    if isinstance(literal, object_search_parser.Text):
        return literal, None

    search_notes.append(('error', "Invalid search query", 0, None))
    return false(), None


def transform_unary_operation_to_query(data, operator, operand, search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]) -> typing.Tuple[Expression, typing.Optional[typing.Callable]]:
    start_token = operator
    start = start_token.start_position
    end_token = operand
    while isinstance(end_token, list):
        end_token = end_token[0]
    end = end_token.start_position + len(end_token.input_text)
    operand, outer_filter = transform_tree_to_query(data, operand, search_notes)
    if not outer_filter:
        def outer_filter(filter):
            return filter

    str_operator = operator.operator
    operator_aliases = {
        '!': 'not'
    }
    if str_operator in operator_aliases:
        str_operator = operator_aliases[str_operator]

    if isinstance(operand, object_search_parser.Boolean):
        operand_type = datatypes.Boolean
    elif isinstance(operand, object_search_parser.Date):
        operand_type = datatypes.DateTime
    elif isinstance(operand, object_search_parser.Quantity):
        operand_type = datatypes.Quantity
    elif isinstance(operand, object_search_parser.Text):
        operand_type = datatypes.Text
    elif isinstance(operand, Attribute):
        operand_type = Attribute
    else:
        operand_type = None

    if (operand_type, str_operator) in unary_operator_handlers:
        return unary_operator_handlers[(operand_type, str_operator)](operator, operand, outer_filter, search_notes)

    search_notes.append(('error', "Unknown unary operation", start, end))
    return Expression(operator.input_text + operand.input_text, operator.start_position, false()), None


def transform_binary_operation_to_query(data, left_operand, operator, right_operand, search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]) -> typing.Tuple[Expression, typing.Optional[typing.Callable]]:
    start_token = left_operand
    while isinstance(start_token, list):
        start_token = start_token[0]
    start = start_token.start_position
    end_token = right_operand
    while isinstance(end_token, list):
        end_token = end_token[-1]
    end = end_token.start_position + len(end_token.input_text)

    left_operand, left_outer_filter = transform_tree_to_query(data, left_operand, search_notes)
    right_operand, right_outer_filter = transform_tree_to_query(data, right_operand, search_notes)

    if left_outer_filter and right_outer_filter:
        search_notes.append(('error', "Multiple array placeholders", start, end))
        return Expression(left_operand.input_text + operator.input_text + right_operand.input_text, left_operand.start_position, false()), None
    if left_outer_filter:
        outer_filter = left_outer_filter
    elif right_outer_filter:
        outer_filter = right_outer_filter
    else:
        def outer_filter(filter):
            return filter

    str_operator = operator.operator
    operator_aliases = {
        '||': 'or',
        '&&': 'and',
        '=': '=='
    }
    if str_operator in operator_aliases:
        str_operator = operator_aliases[str_operator]

    if isinstance(left_operand, object_search_parser.Boolean):
        left_operand_type = datatypes.Boolean
    elif isinstance(left_operand, object_search_parser.Date):
        left_operand_type = datatypes.DateTime
    elif isinstance(left_operand, object_search_parser.Quantity):
        left_operand_type = datatypes.Quantity
    elif isinstance(left_operand, object_search_parser.Text):
        left_operand_type = datatypes.Text
    elif isinstance(left_operand, Attribute):
        left_operand_type = Attribute
    else:
        left_operand_type = None

    if isinstance(right_operand, object_search_parser.Boolean):
        right_operand_type = datatypes.Boolean
    elif isinstance(right_operand, object_search_parser.Date):
        right_operand_type = datatypes.DateTime
    elif isinstance(right_operand, object_search_parser.Quantity):
        right_operand_type = datatypes.Quantity
    elif isinstance(right_operand, object_search_parser.Text):
        right_operand_type = datatypes.Text
    elif isinstance(right_operand, Attribute):
        right_operand_type = Attribute
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
        return binary_operator_handlers[(left_operand_type, right_operand_type, str_operator)](left_operand, operator, right_operand, outer_filter, search_notes)

    search_notes.append(('error', "Unknown binary operation", start, end))
    return Expression(left_operand.input_text + operator.input_text + right_operand.input_text, left_operand.start_position, false()), None


def transform_tree_to_query(data, tree: typing.Union[object_search_parser.Literal, list], search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]) -> typing.Tuple[Expression, typing.Optional[typing.Callable]]:
    if isinstance(tree, object_search_parser.Literal):
        return transform_literal_to_query(data, tree, search_notes)
    if not isinstance(tree, list):
        search_notes.append(('error', "Invalid search query", 0, None))
        return false(), None
    if len(tree) == 1:
        value, = tree
        return transform_tree_to_query(data, value, search_notes)
    if len(tree) == 2:
        operator, operand = tree
        if isinstance(operator, object_search_parser.Operator):
            return transform_unary_operation_to_query(data, operator, operand, search_notes)
        search_notes.append(('error', "Invalid search query (missing operator)", 0, None))
        return false(), None
    if len(tree) == 3:
        left_operand, operator, right_operand = tree
        if isinstance(operator, object_search_parser.Operator):
            return transform_binary_operation_to_query(data, left_operand, operator, right_operand, search_notes)
        search_notes.append(('error', "Invalid search query (missing operator)", 0, None))
        return false(), None


def should_use_advanced_search(query_string: str) -> typing.Tuple[bool, str]:
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


def generate_filter_func(query_string: str, use_advanced_search: bool) -> typing.Tuple[typing.Callable, typing.Any, bool]:
    """
    Generates a filter function for use with SQLAlchemy and the JSONB data
    attribute in the object tables.

    The generated filter functions can be used for objects.get_objects()

    :param query_string: the query string
    :param use_advanced_search: whether to use simple text search (False) or advanced search (True)
    :return: filter func, search tree and whether the advanced search was used
    """
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
                def filter_func(data, search_notes, e=e):
                    """ Return no objects and set search_notes"""
                    search_notes.append(('error', e.message, e.start, e.end))
                    return False
                return filter_func, None, use_advanced_search
            except Exception:
                def filter_func(data, search_notes, start=0, end=len(query_string)):
                    """ Return no objects and set search_notes"""
                    search_notes.append(('error', "Failed to parse query string", start, end))
                    return False
                return filter_func, None, use_advanced_search
            if isinstance(tree, list) and not tree:
                def filter_func(data, search_notes, start=0, end=len(query_string)):
                    """ Return no objects and set search_notes"""
                    search_notes.append(('error', 'Empty search', start, end))
                    return False
                return filter_func, None, use_advanced_search
            if isinstance(tree, object_search_parser.Literal):
                if isinstance(tree, object_search_parser.Boolean):
                    if tree.value.value:
                        def filter_func(data, search_notes, start=0, end=len(query_string)):
                            """ Return all objects and set search_notes"""
                            search_notes.append(('warning', 'This search will always return all objects', start, end))
                            return True
                        return filter_func, tree, use_advanced_search
                    else:
                        def filter_func(data, search_notes, start=0, end=len(query_string)):
                            """ Return no objects and set search_notes"""
                            search_notes.append(('warning', 'This search will never return any objects', start, end))
                            return False
                        return filter_func, tree, use_advanced_search
                elif isinstance(tree, object_search_parser.Attribute):
                    pass
                elif isinstance(tree, object_search_parser.Tag):
                    pass
                else:
                    def filter_func(data, search_notes, start=0, end=len(query_string)):
                        """ Return no objects and set search_notes"""
                        search_notes.append(('error', 'Unable to use literal as search query', start, end))
                        return False
                    return filter_func, None, use_advanced_search

            def filter_func(data, search_notes, tree=tree):
                """ Filter objects based on search query string """
                filter_func, outer_filter = transform_tree_to_query(data, tree, search_notes)
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
            def filter_func(data, search_notes, query_string=query_string):
                """ Filter objects based on search query string """
                # The query string is converted to json to escape quotes, backslashes, etc
                query_string = json.dumps(query_string)[1:-1]
                return data.cast(String).ilike('%: "%' + query_string + '%"%')
    else:
        def filter_func(data, search_notes):
            """ Return all objects"""
            return True
    return filter_func, tree, use_advanced_search


def wrap_filter_func(filter_func):
    """
    Wrap a filter function so that a new list will be filled with the search notes.

    :param filter_func: the filter function to wrap
    :return: the wrapped filter function and the search notes list
    """
    search_notes = []

    def wrapped_filter_func(*args, search_notes=search_notes, filter_func_impl=filter_func, **kwargs):
        return filter_func_impl(*args, search_notes=search_notes, **kwargs)

    return wrapped_filter_func, search_notes
