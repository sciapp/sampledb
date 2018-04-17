# coding: utf-8
"""

"""

import json
import typing
from sqlalchemy import String
from typing import Any
from . import where_filters
from . import datatypes
from . import node
import sqlalchemy as db

def trans(data, tree, fkt1, fkt2):
    """converts tree by Post-Order pass in the type of data,
    which is set through fkt2"""
    if tree.left is None:
        return fkt1(data, tree.operator)
    else:
        return fkt2(trans(data, tree.left, fkt1, fkt2),
                    trans(data, tree.right, fkt1, fkt2), tree.operator)

def fkt1(data, cond:str):
    """gets treeelement, creates quantity"""
    magnitude=0
    units=""
    len_magnitude = 0
    for i in range(0,len(cond)):
        if(cond[i:i+1].isdigit() == False and cond[i:i] is not "."):
            len_magnitude = i
            break
    if (len_magnitude == 0):
        return data[cond]
    else:
        magnitude = float(cond[0:len_magnitude])
        units = cond[len_magnitude:len(cond)]
        quantity = datatypes.Quantity(magnitude, units)
        return quantity

def fkt2(rg1, rg2, operator) -> Any:
    """returns a filter_func"""
    if (operator == "&&"):
        return db.and_(rg1, rg2)
    if (operator == "||"):
        return db.or_(rg1, rg2)
    if (operator == "=="):
        return where_filters.quantity_equals(rg1, rg2)
    if (operator == ">"):
        return where_filters.quantity_greater_than(rg1, rg2)
    if (operator == "<"):
        return where_filters.quantity_less_than(rg1, rg2)
    if (operator == ">="):
        return where_filters.quantity_greater_than_equals(rg1, rg2)
    if (operator == "<="):
        return where_filters.quantity_less_than_equals(rg1, rg2)


def generate_filter_func(query_string: str) -> typing.Callable:
    """
    Generates a filter function for use with SQLAlchemy and the JSONB data
    attribute in the object tables.

    The generated filter functions can be used for objects.get_objects()

    :param query_string: the query string
    :return: filter func
    """
    if query_string:
        def filter_func(data, query_string=query_string):

            #query_string="mass>=15mg or mass>= 7mg and mass <=11mg"
            """ Filter objects based on search query string """
            query_string = node.replace(query_string)
            Binary_tree = node.parsing_in_tree(query_string)
            return trans(data, Binary_tree, fkt1, fkt2)

    else:
        def filter_func(data):
            """ Return all objects"""
            return True
    return filter_func
