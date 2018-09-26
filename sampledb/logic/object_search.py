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
import types
import sqlalchemy.dialects.postgresql as postgresql


from typing import List, Tuple, Optional


OPERATORLIST = {"<": 2, "<=": 2, ">": 2, ">=": 2, "==": 2, "&&": 1,
                "||": 0}


class Node:
    def __init__(self, operator: str, stringleft:
                 Optional[str], stringright: Optional[str]) -> None:
        """constructor creates tree with operator
        to create left and right tree the strings which are
        left and right from the operator"""
        self.operator = operator
        if stringleft is None:
            self.left = None
        elif stringleft is not None:
            self.left = parsing_in_tree(stringleft)
        else:
            self.left = None
        if stringright is None:
            self.right = None
        elif stringright is not None:
            self.right = parsing_in_tree(stringright)
        else:
            self.right = None


def replace(string: str) -> str:
    """deletes Spaces and converts Operators"""
    string = string.replace(" and ", "&&")
    string = string.replace(" or ", "||")
    string = string.replace(" = ", "==")
    string = string.replace(" above ", ">")
    string = string.replace(" under ", "<")
    string = string.replace(" from ", ">=")
    string = string.replace(" after ", ">")
    string = string.replace("before", "<")
    string = string.replace(" in ", "[]")
    string = string.replace(" ","")
    return string


def search_for_wrong_brackets(input: str) -> bool:
    """returns Ture if Expressions parentheses is correct"""
    if input == "":
        return False
    counter = 0
    for i in range(len(input)):
        if input[i] == "(":
            counter += 1
        if input[i] == ")":
            counter -= 1
            if counter < 0:
                return False
    if counter != 0:
        return False
    return True


def remove_unnecessary_brackets(string: str) -> str:
    """removes Outer brackets recursively"""
    while ("(" in string and
           search_for_wrong_brackets(string[1:len(string)-1]) is True):
        string = string[1:len(string)-1]
    return string


def search_operator(string: str) -> Optional[Tuple[str, int]]:
    """returns tuple with:
    ("Operator with lowest priority as String","his position")"""
    lomgest_operator = 2  # length of the longest operator
    string = remove_unnecessary_brackets(string)
    found_operators = []  # List ("operator as String","position")
    bracketcounter = 0
    for i in range(0, len(string)):
        if string[i] == "(":
            bracketcounter += 1
        if string[i] == ")":
            bracketcounter -= 1
        if bracketcounter == 0:
            for j in range(0, lomgest_operator):
                if (string[i:i+1+j] in OPERATORLIST and
                        (string[i:i+2+j] not in OPERATORLIST)):
                    found_operators.append((string[i:i+1+j], i))
                    i += j+1  # dont find < when operator is <=
    found_operators = sorting_list_by_priority(found_operators)
    if len(found_operators) is not 0:
        return found_operators[0]
    else:
        return None


def parsing_in_tree(string: str) -> Node:
    """recursive
    creates tree calls the constructor of class Node
     abort condition if no operator in string anymore"""
    string = remove_unnecessary_brackets(string)
    pos_and_op = search_operator(string)
    if pos_and_op is None:
        baum = Node(string, None, None)
    else:
        ope = pos_and_op[0]
        left = string[0:pos_and_op[1]]
        right = string[pos_and_op[1]+len(pos_and_op[0]):]
        baum = Node(ope, left, right)
    return baum


def sorting_list_by_priority(found_operators: List) -> List:
    """search operator in string with lowest priority,
    which is furthest forward"""
    found_operators.sort(key=lambda operator: OPERATORLIST[operator[0]],
                         reverse=False)
    return found_operators


#!!!!!!!!!!and!!!!!!!!
def handle_boolean_boolean_and(left_operand, right_operand, outer_filter):
    if left_operand.value and right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None

def handle_expression_expression_and(left_operand, right_operand, outer_filter):
    return outer_filter(and_(left_operand, right_operand)), None

def handle_expression_boolean_and(left_operand, right_operand, outer_filter):
    if right_operand.value:
        return outer_filter(left_operand), None
    else:
        return outer_filter(false()), None

def handle_boolean_expression_and(left_operand, right_operand, outer_filter):
    if left_operand.value:
        return outer_filter(right_operand), None
    else:
        return outer_filter(false()), None

def handle_expression_attribute_and(left_operand, right_operand, outer_filter):
    return outer_filter(and_(left_operand, where_filters.boolean_true(right_operand))), None

def handle_attribute_expression_and(left_operand, right_operand, outer_filter):
    return outer_filter(and_(where_filters.boolean_true(left_operand), right_operand)), None

def handle_attribute_boolean_and(left_operand, right_operand, outer_filter):
    if right_operand.value:
        return outer_filter(where_filters.boolean_true(left_operand)), None
    else:
        return outer_filter(false())

def handle_boolean_attribute_and(left_operand, right_operand, outer_filter):
    if left_operand.value:
        return outer_filter(where_filters.boolean_true(right_operand)), None
    else:
        return outer_filter(false())

def handle_attribute_attribute_and(left_operand, right_operand, outer_filter):
    return outer_filter(and_(where_filters.boolean_true(left_operand), where_filters.boolean_true(right_operand))), None

#!!!!!!!!!or!!!!!!!!
def handle_boolean_boolean_or(left_operand, right_operand, outer_filter):
    if left_operand.value or right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None

def handle_expression_expression_or(left_operand, right_operand, outer_filter):
    return outer_filter(or_(left_operand, right_operand)), None

def handle_expression_boolean_or(left_operand, right_operand, outer_filter):
    if right_operand.value:
        return outer_filter(true), None
    else:
        return outer_filter(left_operand), None

def handle_boolean_expression_or(left_operand, right_operand, outer_filter):
    if left_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(left_operand), None

def handle_expression_attribute_or(left_operand, right_operand, outer_filter):
    return outer_filter(or_(left_operand, where_filters.boolean_true(right_operand))), None

def handle_attribute_expression_or(left_operand, right_operand, outer_filter):
    return outer_filter(or_(where_filters.boolean_true(left_operand), right_operand)), None

def handle_attribute_boolean_or(left_operand, right_operand, outer_filter):
    if right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(where_filters.boolean_true(left_operand))

def handle_boolean_attribute_or(left_operand, right_operand, outer_filter):
    if left_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(where_filters.boolean_true(right_operand))

def handle_attribute_attribute_or(left_operand, right_operand, outer_filter):
    return outer_filter(or_(where_filters.boolean_true(left_operand), where_filters.boolean_true(right_operand))), None

#!!!!!!!!!!==!!!!!!!!!!!

def handle_boolean_boolean_equal(left_operand, right_operand, outer_filter):
    if left_operand.value == right_operand.value:
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None

def handle_boolean_attributee_equal(left_operand, right_operand, outer_filter):
    if left_operand.value == where_filters.boolean_true(right_operand):
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None

def handle_attributee_boolean_equal(left_operand, right_operand, outer_filter):
    if right_operand.value == where_filters.boolean_true(left_operand):
        return outer_filter(true()), None
    else:
        return outer_filter(false()), None

def handle_date_date_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_equals(left_operand, right_operand)), None

def handle_attribute_date_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_equals(left_operand, right_operand)), None

def handle_date_attribute_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_equals(left_operand, right_operand)), None

def handle_quantity_quantity_equal(left_operand, right_operand, outer_filter):
    return outer_filter(left_operand == right_operand)

def handle_quantity_attribute_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_equals(right_operand, left_operand)), None

def handle_attribute_quantity_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_equals(left_operand, right_operand)), None

def handle_text_text_equal(left_operand, right_operand, outer_filter):
    return outer_filter(left_operand == right_operand)

def handle_text_attribute_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_equals(right_operand, left_operand)), None

def handle_attribute_text_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_equals(left_operand, right_operand)), None

def handle_attribute_attribute_equal(left_operand, right_operand, outer_filter):
    return outer_filter(left_operand == right_operand), None

def handle_expression_expression_equal(left_operand, right_operand, outer_filter):
    return outer_filter(left_operand == right_operand), None

#!!!!!!!!!<!!!!!!!!!

def handle_date_date_lower(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_less_than(left_operand, right_operand)), None

def handle_quantity_quantity_lower(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_less_than(left_operand, right_operand)), None

def handle_attribute_quantity_lower(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_less_than(left_operand, right_operand)), None

def handle_quantity_attribute_lower(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_greater_than_equals(left_operand, right_operand)), None

def handle_attribute_date_lower(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_less_than(left_operand, right_operand)), None

def handle_date_attribute_lower(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_greater_than_equals(left_operand, right_operand)), None

#!!!!!!!!!!>!!!!!!!!!!!

def handle_date_date_higher(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_greater_than(left_operand, right_operand)), None

def handle_quantity_quantity_higher(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_greater_than(left_operand, right_operand)), None

def handle_attribute_quantity_higher(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_greater_than(left_operand, right_operand)), None

def handle_quantity_attribute_higher(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_less_than_equals(left_operand, right_operand)), None

def handle_attribute_date_higher(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_greater_than(left_operand, right_operand)), None

def handle_date_attribute_higher(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_less_than_equals(left_operand, right_operand)), None

#!!!!!!!!!<=!!!!!!!!!!

def handle_date_date_lower_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_less_than_equals(left_operand, right_operand)), None

def handle_quantity_quantity_lower_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_less_than_equals(left_operand, right_operand)), None

def handle_attribute_quantity_lower_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_less_than_equals(left_operand, right_operand)), None

def handle_quantity_attribute_lower_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_greater_than_equals(right_operand, left_operand)), None

def handle_attribute_date_lower_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_less_than_equals(left_operand, right_operand)), None

def handle_date_attribute_lower_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_greater_than_equals(right_operand, left_operand)), None

#!!!!!!!!>=!!!!!!!!!!

def handle_date_date_higher_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_greater_than_equals(left_operand, right_operand)), None

def handle_quantity_quantity_higher_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_greater_than_equals(left_operand, right_operand)), None

def handle_attribute_quantity_higher_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_greater_than_equals(left_operand, right_operand)), None

def handle_quantity_attribute_higher_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.quantity_less_than_equals(right_operand, left_operand)), None

def handle_attribute_date_higher_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_greater_than_equals(left_operand, right_operand)), None

def handle_date_attribute_higher_or_equal(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.datetime_less_than_equals(right_operand, left_operand)), None

#!!!!!!![]!!!!!!!!!!! in

def handle_attribute_text_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(left_operand,right_operand)), None

def handle_text_attribute_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(right_operand, left_operand)), None

def handle_text_text_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(left_operand, right_operand)), None

def handle_expression_text_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(left_operand, right_operand)), None

def handle_text_expression_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(right_operand, left_operand)), None

def handle_date_text_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(left_operand, right_operand)), None

def handle_text_date_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(right_operand, left_operand)), None

def handle_quantity_text_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(left_operand, right_operand)), None

def handle_text_quantity_contains(left_operand, right_operand, outer_filter):
    return outer_filter(where_filters.text_contains(right_operand, left_operand)), None


operator_handlers = {}
operator_handlers[(datatypes.Boolean, datatypes.Boolean, "&&")] = handle_boolean_boolean_and
operator_handlers[(None,None, "&&")] = handle_expression_expression_and
operator_handlers[(None, datatypes.Boolean, "&&")] = handle_expression_boolean_and
operator_handlers[(datatypes.Boolean, None, "&&")] = handle_boolean_expression_and
operator_handlers[(None, BinaryExpression, "&&")] = handle_expression_attribute_and
operator_handlers[(BinaryExpression, None, "&&")] = handle_attribute_expression_and
operator_handlers[(BinaryExpression, datatypes.Boolean, "&&")] = handle_attribute_boolean_and
operator_handlers[(datatypes.Boolean, BinaryExpression, "&&")] = handle_boolean_attribute_and
operator_handlers[(BinaryExpression, BinaryExpression, "&&")] = handle_attribute_attribute_and

operator_handlers[(datatypes.Boolean, datatypes.Boolean, "||")] = handle_boolean_boolean_or
operator_handlers[(None, None, "||")] = handle_expression_expression_or
operator_handlers[(None, datatypes.Boolean, "||")] = handle_expression_boolean_or
operator_handlers[(datatypes.Boolean, None, "||")] = handle_boolean_expression_or
operator_handlers[(None, BinaryExpression, "||")] = handle_expression_attribute_or
operator_handlers[(BinaryExpression, None, "||")] = handle_attribute_expression_or
operator_handlers[(BinaryExpression, datatypes.Boolean, "||")] = handle_attribute_boolean_or
operator_handlers[(datatypes.Boolean, BinaryExpression, "||")] = handle_boolean_attribute_or
operator_handlers[(BinaryExpression, BinaryExpression, "||")] = handle_attribute_attribute_or

operator_handlers[(datatypes.Boolean, datatypes.Boolean, "==")] = handle_boolean_boolean_equal
operator_handlers[(datatypes.Boolean, BinaryExpression, "==")] = handle_boolean_attributee_equal
operator_handlers[(BinaryExpression, datatypes.Boolean, "==")] = handle_attributee_boolean_equal
operator_handlers[(datatypes.DateTime, datatypes.DateTime, "==")] = handle_date_date_equal
operator_handlers[(BinaryExpression, datatypes.DateTime, "==")] = handle_attribute_date_equal
operator_handlers[(datatypes.DateTime, BinaryExpression, "==")] = handle_date_attribute_equal
operator_handlers[(datatypes.Quantity, datatypes.Quantity, "==")] = handle_quantity_quantity_equal
operator_handlers[(datatypes.Quantity, BinaryExpression, "==")] = handle_quantity_attribute_equal
operator_handlers[(BinaryExpression, datatypes.Quantity, "==")] = handle_attribute_quantity_equal
operator_handlers[(datatypes.Text, datatypes.Text, "==")] = handle_text_text_equal
operator_handlers[(datatypes.Text, BinaryExpression, "==")] = handle_text_attribute_equal
operator_handlers[(BinaryExpression, datatypes.Text, "==")] = handle_attribute_text_equal
operator_handlers[(BinaryExpression, BinaryExpression, "==")] = handle_attribute_attribute_equal
operator_handlers[(None, None, "==")] = handle_expression_expression_equal

operator_handlers[(datatypes.DateTime, datatypes.DateTime,"<")] = handle_date_date_lower
operator_handlers[(datatypes.Quantity, datatypes.Quantity, "<")] = handle_quantity_quantity_lower
operator_handlers[(BinaryExpression, datatypes.Quantity, "<")] = handle_attribute_quantity_lower
operator_handlers[(datatypes.Quantity, BinaryExpression, "<")] = handle_quantity_attribute_lower
operator_handlers[(BinaryExpression, datatypes.DateTime, "<")] = handle_attribute_date_lower
operator_handlers[(datatypes.DateTime, BinaryExpression, "<")] = handle_date_attribute_lower

operator_handlers[(datatypes.DateTime, datatypes.DateTime, ">")] = handle_date_date_higher
operator_handlers[(datatypes.Quantity, datatypes.Quantity, ">")] = handle_quantity_quantity_higher
operator_handlers[(BinaryExpression, datatypes.Quantity, ">")] = handle_attribute_quantity_higher
operator_handlers[(datatypes.Quantity, BinaryExpression, ">")] = handle_quantity_attribute_higher
operator_handlers[(BinaryExpression, datatypes.DateTime, ">")] = handle_attribute_date_higher
operator_handlers[(datatypes.DateTime, BinaryExpression, ">")] = handle_date_attribute_higher

operator_handlers[(datatypes.DateTime, datatypes.DateTime, "<=")] = handle_date_date_lower_or_equal
operator_handlers[(datatypes.Quantity, datatypes.Quantity, "<=")] = handle_quantity_quantity_lower_or_equal
operator_handlers[(BinaryExpression, datatypes.Quantity, "<=")] = handle_attribute_quantity_lower_or_equal
operator_handlers[(datatypes.Quantity, BinaryExpression, "<=")] = handle_quantity_attribute_lower_or_equal
operator_handlers[(BinaryExpression, datatypes.DateTime, "<=")] = handle_attribute_date_lower_or_equal
operator_handlers[(datatypes.DateTime, BinaryExpression, "<=")] = handle_date_attribute_lower_or_equal

operator_handlers[(datatypes.DateTime, datatypes.DateTime, ">=")] = handle_date_date_higher_or_equal
operator_handlers[(datatypes.Quantity, datatypes.Quantity, ">=")] = handle_quantity_quantity_higher_or_equal
operator_handlers[(BinaryExpression, datatypes.Quantity, ">=")] = handle_attribute_quantity_higher_or_equal
operator_handlers[(datatypes.Quantity, BinaryExpression, ">=")] = handle_quantity_attribute_higher_or_equal
operator_handlers[(BinaryExpression, datatypes.DateTime, ">=")] = handle_attribute_date_higher_or_equal
operator_handlers[(datatypes.DateTime, BinaryExpression, ">=")] = handle_date_attribute_higher_or_equal

operator_handlers[(BinaryExpression, datatypes.Text, "[]")] = handle_attribute_text_contains
operator_handlers[(datatypes.Text, BinaryExpression, "[]")] = handle_text_attribute_contains
operator_handlers[(datatypes.Text, datatypes.Text, "[]")] = handle_text_text_contains
operator_handlers[(None, datatypes.Text, "[]")] = handle_expression_text_contains
operator_handlers[(datatypes.Text, None, "[]")] = handle_text_expression_contains
operator_handlers[(datatypes.DateTime, datatypes.Text, "[]")] = handle_date_text_contains
operator_handlers[(datatypes.Text, datatypes.DateTime, "[]")] = handle_text_date_contains
operator_handlers[(datatypes.Quantity, datatypes.Text, "[]")] = handle_expression_text_contains
operator_handlers[(datatypes.Text, datatypes.Quantity, "[]")] = handle_text_expression_contains


def transform_tree(data, tree: Node, unary_transformation: typing.Callable, binary_transformation: typing.Callable):


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


def binary_transformation(left_operand_and_filter: typing.Tuple[Any, Any], right_operand_and_filter: typing.Tuple[Any, Any], operator: str) -> (Any, typing.Optional[typing.Callable]):
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

    left_operand_type = None

    left_operand_is_boolean = False
    left_operand_is_date = False
    left_operand_is_quantity = False
    left_operand_is_text = False
    left_operand_is_attribute = False
    left_operand_is_expression = False
    if isinstance(left_operand, datatypes.Boolean): #sets left_operand_type and left_operand_is_datetype=True
        left_operand_is_boolean = True
        left_operand_type = datatypes.Boolean
    elif isinstance(left_operand, datatypes.DateTime):
        left_operand_is_date = True
        left_operand_type = datatypes.DateTime
    elif isinstance(left_operand, datatypes.Quantity):
        left_operand_is_quantity = True
        left_operand_type = datatypes.Quantity
    elif isinstance(left_operand, datatypes.Text):
        left_operand_is_text = True
        left_operand_type = datatypes.Text
    elif isinstance(left_operand, BinaryExpression):
        left_operand_is_attribute = True
        left_operand_type = BinaryExpression
    else:
        left_operand_is_expression = True

    right_operand_type = None

    right_operand_is_boolean = False
    right_operand_is_date = False
    right_operand_is_quantity = False
    right_operand_is_text = False
    right_operand_is_attribute = False
    right_operand_is_expression = False
    if isinstance(right_operand, datatypes.Boolean): #sets right_operand_type and right_operand_is_datetype=True
        right_operand_is_boolean = True
        right_operand_type = datatypes.Boolean
    elif isinstance(right_operand, datatypes.DateTime):
        right_operand_is_date = True
        right_operand_type = datatypes.DateTime
    elif isinstance(right_operand, datatypes.Quantity):
        right_operand_is_quantity = True
        right_operand_type = datatypes.Quantity
    elif isinstance(right_operand, datatypes.Text):
        right_operand_is_text = True
        right_operand_type = datatypes.Text
    elif isinstance(right_operand, BinaryExpression):
        right_operand_is_attribute = True
        right_operand_type = BinaryExpression
    else:
        right_operand_is_expression = True

    if (left_operand_type, right_operand_type, operator) in operator_handlers:
        return operator_handlers[(left_operand_type, right_operand_type, operator)](left_operand, right_operand, outer_filter)


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
                query_string = replace(query_string)
                binary_tree = parsing_in_tree(query_string)
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