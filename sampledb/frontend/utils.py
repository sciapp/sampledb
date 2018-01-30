# coding: utf-8
"""

"""

import os
import flask

from ..logic.units import prettify_units


def jinja_filter(func):
    global _jinja_filters
    _jinja_filters[func.__name__] = func
    return func

_jinja_filters = {}
jinja_filter.filters = _jinja_filters


def has_preview(file_name):
    file_extension = os.path.splitext(file_name)[1]
    return file_extension in flask.current_app.config.get('MIME_TYPES', {})


def is_image(file_name):
    file_extension = os.path.splitext(file_name)[1]
    return flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, '').startswith('image/')


_jinja_filters['prettify_units'] = prettify_units
_jinja_filters['has_preview'] = has_preview
_jinja_filters['is_image'] = is_image
