# coding: utf-8
"""

"""

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class SchemaError(Exception):
    def __init__(self, message, path):
        if path:
            message += ' (at ' + ' -> '.join(path) + ')'
        super(SchemaError, self).__init__(message)
        self.path = path
        self.message = message
        self.paths = [path]


class ValidationError(SchemaError):
    def __init__(self, message, path):
        super(ValidationError, self).__init__(message, path)


class ValidationMultiError(ValidationError):
    def __init__(self, errors):
        message = '\n'.join(error.message for error in errors)
        super(ValidationMultiError, self).__init__(message, [])
        self.paths = [error.path for error in errors]
