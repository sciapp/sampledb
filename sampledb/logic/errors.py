# coding: utf-8
"""

"""

# These are imported to allow uniform access to logic errors
# noinspection PyUnresolvedReferences
from .schemas.errors import SchemaError, ValidationError


class ObjectDoesNotExistError(Exception):
    pass


class ObjectVersionDoesNotExistError(Exception):
    pass


class GroupDoesNotExistError(ValueError):
    pass


class GroupAlreadyExistsError(ValueError):
    pass


class UserDoesNotExistError(ValueError):
    pass


class UserNotMemberOfGroupError(ValueError):
    pass


class UserAlreadyMemberOfGroupError(ValueError):
    pass


class InvalidGroupNameError(ValueError):
    pass