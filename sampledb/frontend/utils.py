# coding: utf-8
"""

"""


def jinja_filter(func):
    global _jinja_filters
    _jinja_filters[func.__name__] = func
    return func

_jinja_filters = {}
jinja_filter.filters = _jinja_filters
