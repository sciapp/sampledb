# coding: utf-8
"""

"""

import json
from sqlalchemy import String
from . import where_filters


def generate_filter_func(query_string):
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
