# coding: utf-8
"""

"""

import json
import typing
from sqlalchemy import String
from . import where_filters


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
            """ Filter objects based on search query string """
            # Simple search in values
            # The query string is converted to json to escape quotes, backslashes, etc
            query_string = json.dumps(query_string)[1:-1]
            return data.cast(String).like('%: "%'+query_string+'%"%')
    else:
        def filter_func(data):
            """ Return all objects"""
            return True
    return filter_func
