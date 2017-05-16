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
