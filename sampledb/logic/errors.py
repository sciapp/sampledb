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


class InvalidFileStorageError(Exception):
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


class ProjectAlreadyExistsError(Exception):
    pass


class InvalidProjectNameError(Exception):
    pass


class ProjectDoesNotExistError(Exception):
    pass


class UserNotMemberOfProjectError(Exception):
    pass


class UserAlreadyMemberOfProjectError(Exception):
    pass


class GroupAlreadyMemberOfProjectError(Exception):
    pass


class GroupNotMemberOfProjectError(Exception):
    pass


class NoMemberWithGrantPermissionsForProjectError(Exception):
    pass


class InvalidSubprojectRelationshipError(Exception):
    pass


class SubprojectRelationshipDoesNotExistError(Exception):
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


class LocationDoesNotExistError(Exception):
    pass


class CyclicLocationError(Exception):
    pass


class ObjectLocationAssignmentDoesNotExistError(Exception):
    pass


class NotificationDoesNotExistError(Exception):
    pass


class OnlyOneAuthenticationMethod(Exception):
    pass


class AuthenticationMethodWrong(Exception):
    pass


class AuthenticationMethodAlreadyExists(Exception):
    pass


class NoEmailInLDAPAccountError(Exception):
    pass


class LDAPAccountAlreadyExistError(Exception):
    pass


class LDAPAccountOrPasswordWrongError(Exception):
    pass


class PublicationDoesNotExistError(Exception):
    pass


class InvalidDOIError(Exception):
    pass


class LDAPNotConfiguredError(Exception):
    pass


class UserIsReadonlyError(Exception):
    pass


class InstrumentLogEntryDoesNotExistError(Exception):
    pass


class InstrumentLogFileAttachmentDoesNotExistError(Exception):
    pass


class InstrumentLogObjectAttachmentDoesNotExistError(Exception):
    pass


class InstrumentLogCategoryDoesNotExistError(Exception):
    pass


class GroupInvitationDoesNotExistError(Exception):
    pass


class ProjectInvitationDoesNotExistError(Exception):
    pass


class UserInvitationDoesNotExistError(Exception):
    pass


class ActionTypeDoesNotExistError(Exception):
    pass


class CommentDoesNotExistError(Exception):
    pass


class DataverseNotReachableError(Exception):
    pass


class ProjectObjectLinkDoesNotExistsError(Exception):
    pass


class ProjectObjectLinkAlreadyExistsError(Exception):
    pass


class LanguageDoesNotExistError(Exception):
    pass


class ActionTranslationDoesNotExistError(Exception):
    pass


class ActionTypeTranslationDoesNotExistError(Exception):
    pass


class InstrumentTranslationDoesNotExistError(Exception):
    pass


class MissingEnglishTranslationError(Exception):
    pass


class InvalidNumberError(Exception):
    pass


class LanguageAlreadyExistsError(Exception):
    pass


class TwoFactorAuthenticationMethodDoesNotExistError(Exception):
    pass
