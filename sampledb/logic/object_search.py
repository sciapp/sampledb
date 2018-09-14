# coding: utf-8

import json
import typing
import datetime
from sqlalchemy import String, and_, or_
from sqlalchemy import String, Float, and_, or_
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.expression import select, exists, true, false
from typing import Any
from . import where_filters
from . import datatypes
from . import node
from .. import db
import sqlalchemy.dialects.postgresql as postgresql


def transform_tree(data, tree, unary_transformation, binary_transformation):


    if tree.left is None:
        return unary_transformation(data, tree.operator)
    else:
        left_operand = transform_tree(data, tree.left, unary_transformation, binary_transformation)
        right_operand = transform_tree(data, tree.right, unary_transformation, binary_transformation)
        return binary_transformation(left_operand, right_operand, tree.operator)

def validate(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')

        return True
    except ValueError:
        return False


def unary_transformation(data: Column, operand: str) -> typing.Tuple[typing.Union[datatypes.Quantity, datatypes.DateTime, datatypes.Text, datatypes.Boolean, BinaryExpression], typing.Optional[typing.Callable]]:
    """gets treeelement, creates quantity or date"""

    if validate(operand):
        operand = datetime.datetime.strptime(operand, '%Y-%m-%d')
        date = datatypes.DateTime(operand)
        return date, None

    had_decimal_point = False
    len_magnitude = 0

    for index, character in enumerate(operand):
        if not character.isdigit():
            if not had_decimal_point and character == ".":
                had_decimal_point = True
            else:
                len_magnitude = index
                break
        else:
            len_magnitude = len(operand)
    if len_magnitude > 0:
        magnitude = float(operand[:len_magnitude])
        units = operand[len_magnitude:]
        if not units:
            units = None
        quantity = datatypes.Quantity(magnitude, units)
        return quantity, None

    if operand.startswith('"') and operand.endswith('"') and len(operand) >= 2:
        return datatypes.Text(operand[1:-1]), None

    if operand.lower() == 'true':
        return datatypes.Boolean(True), None

    if operand.lower() == 'false':
        return datatypes.Boolean(False), None

    # Try parsing cond as attribute
    attributes = operand.split('.')
    for attribute in attributes:
        if not all(character.isalnum() or character in '_?' for character in attribute):
            # TODO: better error
            raise ValueError("Invalid attribute name")
        if '?' in attribute and attribute != '?':
            raise ValueError("Array index placeholder must stand alone")
    # covert any numeric arguments to integers (array indices)
    for i, attribute in enumerate(attributes):
        try:
            attributes[i] = int(attribute)
        except ValueError:
            pass
    if '?' in attributes:
        if attributes.count('?') > 1:
            raise ValueError("Only one array index placeholder is supported")
        array_placeholder_index = attributes.index('?')
        # no danger of SQL injection as attributes may only consist of
        # characters and underscores at this point
        jsonb_selector = '\'' + '\' -> \''.join(attributes[:array_placeholder_index]) + '\''
        array_items = select(columns=[db.text('value FROM jsonb_array_elements_text(data -> {})'.format(jsonb_selector))])
        db_obj = db.literal_column('value').cast(postgresql.JSONB)
        for attribute in attributes[array_placeholder_index+1:]:
            db_obj = db_obj[attribute]
        return db_obj, lambda filter: db.Query(db.literal(True)).select_entity_from(array_items).filter(filter).exists()
    return data[attributes], None


def binary_transformation(left_operand_and_filter, right_operand_and_filter, operator) -> (Any, typing.Optional[typing.Callable]):
    """returns a filter_func"""

    left_operand, left_outer_filter = left_operand_and_filter
    right_operand, right_outer_filter = right_operand_and_filter

    if left_outer_filter and right_outer_filter:
        raise ValueError("Only one outer filter is supported")
    if left_outer_filter:
        outer_filter = left_outer_filter
    elif right_outer_filter:
        outer_filter = right_outer_filter
    else:
        outer_filter = lambda filter: filter

    left_operand_is_boolean = False
    left_operand_is_date = False
    left_operand_is_quantity = False
    left_operand_is_text = False
    left_operand_is_attribute = False
    left_operand_is_expression = False
    if isinstance(left_operand, datatypes.Boolean):
        left_operand_is_boolean = True
    elif isinstance(left_operand, datatypes.DateTime):
        left_operand_is_date = True
    elif isinstance(left_operand, datatypes.Quantity):
        left_operand_is_quantity = True
    elif isinstance(left_operand, datatypes.Text):
        left_operand_is_text = True
    elif isinstance(left_operand, BinaryExpression):
        left_operand_is_attribute = True
    else:
        left_operand_is_expression = True

    right_operand_is_boolean = False
    right_operand_is_date = False
    right_operand_is_quantity = False
    right_operand_is_text = False
    right_operand_is_attribute = False
    right_operand_is_expression = False
    if isinstance(right_operand, datatypes.Boolean):
        right_operand_is_boolean = True
    elif isinstance(right_operand, datatypes.DateTime):
        right_operand_is_date = True
    elif isinstance(right_operand, datatypes.Quantity):
        right_operand_is_quantity = True
    elif isinstance(right_operand, datatypes.Text):
        right_operand_is_text = True
    elif isinstance(right_operand, BinaryExpression):
        right_operand_is_attribute = True
    else:
        right_operand_is_expression = True

    if operator == "&&":
        if left_operand_is_expression and right_operand_is_expression:
            return outer_filter(and_(left_operand, right_operand)), None
        elif left_operand_is_boolean and right_operand_is_expression:
            if left_operand.value:
                return outer_filter(right_operand), None
            else:
                return outer_filter(false()), None
        elif left_operand_is_expression and right_operand_is_boolean:
            if right_operand.value:
                return outer_filter(left_operand), None
            else:
                return outer_filter(false()), None
        elif left_operand_is_boolean and right_operand_is_boolean:
            if left_operand == right_operand:
                return outer_filter(true()), None
            else:
                return outer_filter(false()), None
        elif left_operand_is_attribute and right_operand_is_expression:
            return outer_filter(and_(where_filters.boolean_true(left_operand), right_operand)), None
        elif left_operand_is_expression and right_operand_is_attribute:
            return outer_filter(and_(left_operand, where_filters.boolean_true(right_operand))), None
        elif left_operand_is_attribute and right_operand_is_boolean:
            if right_operand.value:
                return outer_filter(where_filters.boolean_true(left_operand)), None
            else:
                return outer_filter(false()), None
        elif left_operand_is_boolean and right_operand_is_attribute:
            if left_operand.value:
                return outer_filter(where_filters.boolean_true(right_operand)), None
            else:
                return outer_filter(false()), None
        elif left_operand_is_attribute and right_operand_is_attribute:
            return outer_filter(and_(where_filters.boolean_true(left_operand), where_filters.boolean_true(right_operand))), None
        else:
            # TODO: print warning for user
            return outer_filter(false()), None
    if operator == "||":
        return outer_filter(or_(left_operand, right_operand)), None
    if operator == "==" or operator == '=':
        if left_operand_is_boolean or right_operand_is_boolean:
            if left_operand_is_boolean and right_operand_is_boolean:
                if left_operand == right_operand:
                    return outer_filter(true()), None
                else:
                    return outer_filter(false()), None
            elif left_operand_is_attribute and right_operand_is_boolean:
                return outer_filter(where_filters.boolean_equals(left_operand, right_operand)), None
            elif left_operand_is_boolean and right_operand_is_attribute:
                return outer_filter(where_filters.boolean_equals(right_operand, left_operand)), None
            else:
                # TODO: print warning for user
                return outer_filter(false()), None
        if left_operand_is_date or right_operand_is_date:
            if left_operand_is_date and right_operand_is_date:
                return left_operand == right_operand
            elif left_operand_is_attribute and right_operand_is_date:
                return outer_filter(where_filters.datetime_equals(left_operand, right_operand)), None
            elif left_operand_is_date and right_operand_is_attribute:
                return outer_filter(where_filters.datetime_equals(right_operand, left_operand)), None
            else:
                # TODO: print warning for user
                return outer_filter(false()), None
        if left_operand_is_quantity or right_operand_is_quantity:
            if left_operand_is_quantity and right_operand_is_quantity:
                return left_operand == right_operand
            elif left_operand_is_attribute and right_operand_is_quantity:
                return outer_filter(where_filters.quantity_equals(left_operand, right_operand)), None
            elif left_operand_is_quantity and right_operand_is_attribute:
                return outer_filter(where_filters.quantity_equals(right_operand, left_operand)), None
            else:
                # TODO: print warning for user
                return outer_filter(false()), None
        if left_operand_is_text or right_operand_is_text:
            if left_operand_is_text and right_operand_is_text:
                return left_operand == right_operand
            elif left_operand_is_attribute and right_operand_is_text:
                return outer_filter(where_filters.text_equals(left_operand, right_operand)), None
            elif left_operand_is_text and right_operand_is_attribute:
                return outer_filter(where_filters.text_equals(right_operand, left_operand)), None
            else:
                # TODO: print warning for user
                return outer_filter(false()), None
        if left_operand_is_attribute and right_operand_is_attribute:
            return left_operand == right_operand, None
        if left_operand_is_expression and right_operand_is_expression:
            return left_operand == right_operand, None
        # TODO: print warning for user
        return outer_filter(false()), None
    if operator == ">":
        if right_operand_is_date:
            return outer_filter(where_filters.datetime_greater_than(left_operand, right_operand)), None
        else:
            return outer_filter(where_filters.quantity_greater_than(left_operand, right_operand)), None
    if operator == "<":
        if right_operand_is_date:
            return outer_filter(where_filters.datetime_less_than(left_operand, right_operand)), None
        else:
            return outer_filter(where_filters.quantity_less_than(left_operand, right_operand)), None
    if operator == ">=":
        if right_operand_is_date:
            return outer_filter(where_filters.datetime_greater_than_equals(left_operand, right_operand)), None
        else:
            return outer_filter(where_filters.quantity_greater_than_equals(left_operand, right_operand)), None
    if operator == "<=":
        if right_operand_is_date:
            return outer_filter(where_filters.datetime_less_than_equals(left_operand, right_operand)), None
        else:
            return outer_filter(where_filters.quantity_less_than_equals(left_operand, right_operand)), None

    return False


def generate_filter_func(query_string: str, use_advanced_search: bool) -> typing.Callable:
    """
    Generates a filter function for use with SQLAlchemy and the JSONB data
    attribute in the object tables.

    The generated filter functions can be used for objects.get_objects()

    :param query_string: the query string
    :param use_advanced_search: whether to use simple text search (False) or advanced search (True)
    :return: filter func
    """
    if query_string:
        if use_advanced_search:
            # Advanced search using parser and where_filters
            def filter_func(data, query_string=query_string):
                """ Filter objects based on search query string """
                query_string = node.replace(query_string)
                binary_tree = node.parsing_in_tree(query_string)
                return transform_tree(data, binary_tree, unary_transformation, binary_transformation)[0]
        else:
            # Simple search in values
            def filter_func(data, query_string=query_string):
                """ Filter objects based on search query string """
                # The query string is converted to json to escape quotes, backslashes, etc
                query_string = json.dumps(query_string)[1:-1]
                return data.cast(String).like('%: "%'+query_string+'%"%')
    else:
        def filter_func(data):
            """ Return all objects"""
            return True
    return filter_func