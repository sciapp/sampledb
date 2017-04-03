# coding: utf-8
"""

"""

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class SchemaError(Exception):
    def __init__(self, message, path):
        message += ' (at ' + ' -> '.join(path) + ')'
        super(SchemaError, self).__init__(message)


class ValidationError(SchemaError):
    def __init__(self, message, path):
        super(ValidationError, self).__init__(message, path)
