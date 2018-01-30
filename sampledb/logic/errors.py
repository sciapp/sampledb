# coding: utf-8
"""

"""


class ObjectDoesNotExistError(Exception):
    pass


class FileDoesNotExistError(Exception):
    pass


class ObjectVersionDoesNotExistError(Exception):
    pass


class FileNameTooLongError(Exception):
    pass


class TooManyFilesForObjectError(Exception):
    pass


class InvalidFileSourceError(Exception):
    pass


class GroupDoesNotExistError(Exception):
    pass


class GroupAlreadyExistsError(Exception):
    pass


class UserDoesNotExistError(Exception):
    pass


class UserNotMemberOfGroupError(Exception):
    pass


class UserAlreadyMemberOfGroupError(Exception):
    pass


class InvalidGroupNameError(Exception):
    pass


class ActionDoesNotExistError(Exception):
    pass


class InstrumentDoesNotExistError(Exception):
    pass


class UserAlreadyResponsibleForInstrumentError(Exception):
    pass


class UserNotResponsibleForInstrumentError(Exception):
    pass


class UndefinedUnitError(Exception):
    pass


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