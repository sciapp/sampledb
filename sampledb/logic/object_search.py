# coding: utf-8

import json
import typing
import datetime
from sqlalchemy import String, and_, or_
from sqlalchemy import String, Float, and_, or_
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.expression import select, exists
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


def unary_transformation(data: Column, operand: str) -> typing.Tuple[typing.Union[datatypes.Quantity, BinaryExpression], typing.Optional[typing.Callable]]:
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


def binary_transformation(rg1, rg2, operator) -> (Any,Any):
    """returns a filter_func"""

    outer_filter = lambda filter: filter
    if rg1[1] and rg2[1]:
        raise ValueError("Only one outer filter is supported")
    if rg1[1]:
        outer_filter = rg1[1]
    if rg2[1]:
        outer_filter = rg2[1]
    rg2_is_date = False
    if isinstance(rg2[0], datatypes.DateTime):
        rg2_is_date = True
    if (operator == "&&"):
        return outer_filter(and_(rg1[0], rg2[0])),None
    if (operator == "||"):
        return outer_filter(or_(rg1[0], rg2[0])),None
    if (operator == "=="):
        if rg2_is_date:
            return outer_filter(where_filters.datetime_equals(rg1[0], rg2[0])),None
        else:
            return outer_filter(where_filters.quantity_equals(rg1[0], rg2[0])),None
    if (operator == ">"):
        if rg2_is_date:
            return outer_filter(where_filters.datetime_greater_than(rg1[0], rg2[0])),None
        else:
            return outer_filter(where_filters.quantity_greater_than(rg1[0], rg2[0])),None
    if (operator == "<"):
        if rg2_is_date:
            return outer_filter(where_filters.datetime_less_than(rg1[0], rg2[0])),None
        else:
            return outer_filter(where_filters.quantity_less_than(rg1[0], rg2[0])),None
    if (operator == ">="):
        if rg2_is_date:
            return outer_filter(where_filters.datetime_greater_than_equals(rg1[0], rg2[0])),None
        else:
            return outer_filter(where_filters.quantity_greater_than_equals(rg1[0], rg2[0])),None
    if (operator == "<="):
        if rg2_is_date:
            return outer_filter(where_filters.datetime_less_than_equals(rg1[0], rg2[0])),None
        else:
            return outer_filter(where_filters.quantity_less_than_equals(rg1[0], rg2[0])),None


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