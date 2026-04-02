import base64
import datetime
import typing
from contextlib import suppress
from dataclasses import dataclass

import flask
from pydantic import (BaseModel, BeforeValidator, NonNegativeInt, Strict,
                      ValidationInfo, constr, model_validator)
from pydantic_core import PydanticCustomError

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic.instruments import get_instrument
from ...logic.instrument_log_entries import InstrumentLogEntry as LogicInstrumentLogEntry, InstrumentLogFileAttachment, InstrumentLogObjectAttachment, get_instrument_log_entries, get_instrument_log_entry, get_instrument_log_file_attachment, get_instrument_log_object_attachment, get_instrument_log_categories, create_instrument_log_entry, create_instrument_log_file_attachment, create_instrument_log_object_attachment, update_instrument_log_entry, hide_instrument_log_object_attachment, hide_instrument_log_file_attachment
from ...logic import errors, instrument_log_entries
from ...logic.object_permissions import get_user_object_permissions
from ...models import Permissions
from .validation_utils import (Base64Encoded,
                               ModelWithDefaultsFromValidationInfo,
                               ValidatingError, is_valid,
                               populate_missing_or_expect_from_validation_info,
                               validate)

MAX_FILE_NAME_LENGTH = 256


@dataclass(frozen=True, slots=True)
class _ValidationContext:
    log_entry: typing.Optional[LogicInstrumentLogEntry]
    existing_category_ids: frozenset[int]

    @property
    def existing_file_attachments(self) -> typing.List[InstrumentLogFileAttachment]:
        assert self.log_entry is not None
        return [fa for fa in self.log_entry.file_attachments if not fa.is_hidden]

    @property
    def existing_object_attachments(self) -> typing.List[InstrumentLogObjectAttachment]:
        assert self.log_entry is not None
        return [oa for oa in self.log_entry.object_attachments if not oa.is_hidden]


# pyflakes doesn't like string literals in type annotations that don't correspond to a Python identifier
_base64_content = "base64_content"


class _FileAttachment(BaseModel):
    if typing.TYPE_CHECKING:
        file_name: str
        content: bytes
    else:
        file_name: constr(strip_whitespace=True, min_length=1, max_length=MAX_FILE_NAME_LENGTH)
        content: Base64Encoded(_base64_content)


class _ObjectAttachment(BaseModel):
    object_id: typing.Annotated[NonNegativeInt, Strict()]

    @model_validator(mode="after")
    def check_object_exists(self) -> typing.Self:
        try:
            permissions = get_user_object_permissions(self.object_id, flask.g.user.id)
            if Permissions.READ not in permissions:
                raise errors.ObjectDoesNotExistError()
            return self
        except errors.ObjectDoesNotExistError:
            raise PydanticCustomError("no_such_object", "Object should exist")


def _parse_datetime(value: typing.Any) -> datetime.datetime:
    if not isinstance(value, str):
        raise PydanticCustomError("datetime_type", "Input should be a valid timestamp")
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
    except Exception:
        raise PydanticCustomError("datetime_parsing", "Timestamp should be in ISO format including microseconds, e.g. 2024-01-02T03:04:05.678910")


class _BaseInstrumentLogEntry(ModelWithDefaultsFromValidationInfo):
    content: typing.Optional[str]
    content_is_markdown: bool = False
    category_ids: typing.List[
        typing.Annotated[
            int,
            Strict(),
            is_valid(
                lambda v, i: v in i.context.existing_category_ids,
                lambda i: PydanticCustomError(
                    "unexpected",
                    f"Category ID should be one of: {", ".join(map(str, i.context.existing_category_ids))}" if i.context.existing_category_ids else "Category ID does not exist, instrument has no log categories",
                    {"allowed": i.context.existing_category_ids},
                ),
            ),
        ],
    ] = []
    event_utc_datetime: typing.Optional[
        typing.Annotated[
            datetime.datetime,
            BeforeValidator(_parse_datetime),
            is_valid(
                lambda v, i: abs(v - datetime.datetime.now()) <= datetime.timedelta(days=365_242),
                lambda i: PydanticCustomError("datetime_range", "Timestamp should not be more than 1000 years before or after the current date"),
            ),
        ]
    ] = None


_ObjectAttachments = typing.Annotated[
    typing.List[_ObjectAttachment],
    is_valid(
        lambda v, i: len({x.object_id for x in v}) == len(v),
        lambda i: PydanticCustomError("unique", "Object should only be attached once"),
    ),
]


class _InstrumentLogEntry(_BaseInstrumentLogEntry):
    file_attachments: typing.List[_FileAttachment] = []
    object_attachments: _ObjectAttachments = []

    @model_validator(mode="after")
    def check_not_empty(self) -> typing.Self:
        if self.content or self.file_attachments or self.object_attachments:
            return self
        raise PydanticCustomError("log_entry_empty", "Log entry should contain content or an attachment")


class _InstrumentLogEntryVersion(_BaseInstrumentLogEntry):
    version_id: typing.Annotated[int, populate_missing_or_expect_from_validation_info(lambda i: len(i.context.log_entry.versions) + 1)]
    log_entry_id: typing.Annotated[int, populate_missing_or_expect_from_validation_info(lambda i: i.context.log_entry.id)]
    file_attachments: typing.Optional[typing.List[_FileAttachment]] = None
    object_attachments: typing.Optional[_ObjectAttachments] = None

    @model_validator(mode="after")
    def check_not_empty(self, info: ValidationInfo[_ValidationContext]) -> typing.Self:
        file_attachments = info.context.existing_file_attachments if self.file_attachments is None else self.file_attachments
        object_attachments = info.context.existing_object_attachments if self.object_attachments is None else self.object_attachments
        if self.content or file_attachments or object_attachments:
            return self
        raise PydanticCustomError("log_entry_empty", "Log entry should contain content or an attachment")


def instrument_log_entry_to_json(log_entry: instrument_log_entries.InstrumentLogEntry) -> typing.Dict[str, typing.Any]:
    return {
        'log_entry_id': log_entry.id,
        'author': log_entry.user_id,
        'versions': [
            instrument_log_entry_version_to_json(version)
            for version in log_entry.versions
        ]
    }


def instrument_log_entry_version_to_json(version: instrument_log_entries.InstrumentLogEntryVersion) -> typing.Dict[str, typing.Any]:
    return {
        'log_entry_id': version.log_entry_id,
        'version_id': version.version_id,
        'utc_datetime': version.utc_datetime.replace(tzinfo=None).isoformat(timespec='microseconds'),
        'content': version.content,
        'categories': [
            category_to_json(category)
            for category in version.categories
        ],
        'event_utc_datetime': version.event_utc_datetime.replace(tzinfo=None).isoformat(timespec='microseconds') if version.event_utc_datetime is not None else None,
        'content_is_markdown': version.content_is_markdown,
    }


def file_attachment_to_json(file_attachment: instrument_log_entries.InstrumentLogFileAttachment) -> typing.Dict[str, typing.Any]:
    return {
        'file_attachment_id': file_attachment.id,
        'file_name': file_attachment.file_name if not file_attachment.is_hidden else None,
        'base64_content': base64.b64encode(file_attachment.content).decode('ascii') if not file_attachment.is_hidden else None,
        'is_hidden': file_attachment.is_hidden
    }


def object_attachment_to_json(object_attachment: instrument_log_entries.InstrumentLogObjectAttachment) -> typing.Dict[str, typing.Any]:
    return {
        'object_attachment_id': object_attachment.id,
        'object_id': object_attachment.object_id if not object_attachment.is_hidden else None,
        'is_hidden': object_attachment.is_hidden
    }


def category_to_json(category: instrument_log_entries.InstrumentLogCategory) -> typing.Dict[str, typing.Any]:
    return {
        'category_id': category.id,
        'title': category.title
    }


class InstrumentLogEntries(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        log_entries = get_instrument_log_entries(instrument_id)
        return [instrument_log_entry_to_json(log_entry) for log_entry in log_entries]

    @multi_auth.login_required
    def post(self, instrument_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_create_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be created by instrument scientists"
            }, 403
        request_json = flask.request.get_json(force=True)
        try:
            request_data = validate(_InstrumentLogEntry, request_json, context=_ValidationContext(None, frozenset(category.id for category in get_instrument_log_categories(instrument_id))))
        except ValidatingError as e:
            return e.response

        log_entry = create_instrument_log_entry(
            instrument_id=instrument.id,
            user_id=flask.g.user.id,
            content=request_data.content or "",
            content_is_markdown=request_data.content_is_markdown,
            category_ids=request_data.category_ids,
            event_utc_datetime=request_data.event_utc_datetime,
        )

        for file_attachment in request_data.file_attachments:
            create_instrument_log_file_attachment(
                instrument_log_entry_id=log_entry.id,
                file_name=file_attachment.file_name,
                content=file_attachment.content,
            )

        for object_attachment in request_data.object_attachments:
            create_instrument_log_object_attachment(
                instrument_log_entry_id=log_entry.id,
                object_id=object_attachment.object_id,
            )

        return None, 201, {
            'Location': flask.url_for(
                'api.instrument_log_entry',
                instrument_id=instrument_id,
                log_entry_id=log_entry.id,
                _external=True
            )
        }


class InstrumentLogEntry(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return instrument_log_entry_to_json(log_entry)


class InstrumentLogEntryVersions(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return [
            instrument_log_entry_version_to_json(version)
            for version in log_entry.versions
        ]

    @multi_auth.login_required
    def post(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        validation_context = _ValidationContext(log_entry, frozenset(category.id for category in get_instrument_log_categories(instrument_id)))
        request_json = flask.request.get_json(force=True)
        try:
            request_data = validate(_InstrumentLogEntryVersion, request_json, context=validation_context)
        except ValidatingError as e:
            return e.response
        log_entry = update_instrument_log_entry(
            log_entry_id=log_entry.id,
            content=request_data.content or "",
            category_ids=request_data.category_ids,
            content_is_markdown=request_data.content_is_markdown,
            event_utc_datetime=request_data.event_utc_datetime,
        )
        if request_data.file_attachments is not None:
            new_file_attachments = {(file_attachment.file_name, file_attachment.content) for file_attachment in request_data.file_attachments}
            for file_name, content in new_file_attachments.difference(
                    (file_attachment.file_name, file_attachment.content) for file_attachment in validation_context.existing_file_attachments
            ):
                create_instrument_log_file_attachment(
                    instrument_log_entry_id=log_entry.id,
                    file_name=file_name,
                    content=content,
                )
            for file_attachment in validation_context.existing_file_attachments:
                if (file_attachment.file_name, file_attachment.content) not in new_file_attachments:
                    hide_instrument_log_file_attachment(file_attachment.id)
        if request_data.object_attachments is not None:
            new_object_attachments = {object_attachment.object_id for object_attachment in request_data.object_attachments}
            for object_id in new_object_attachments.difference(oa.object_id for oa in log_entry.object_attachments):
                with suppress(errors.ObjectDoesNotExistError):
                    create_instrument_log_object_attachment(log_entry.id, object_id)
            for object_attachment in log_entry.object_attachments:
                should_be_hidden = object_attachment.object_id not in new_object_attachments
                if should_be_hidden != object_attachment.is_hidden:
                    hide_instrument_log_object_attachment(object_attachment.id, set_hidden=should_be_hidden)

        return None, 201, {
            'Location': flask.url_for(
                'api.instrument_log_entry_version',
                instrument_id=instrument_id,
                log_entry_id=log_entry.id,
                log_entry_version_id=log_entry.versions[-1].version_id,
                _external=True
            )
        }


class InstrumentLogEntryVersion(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int, log_entry_version_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        versions_by_id = {
            version.version_id: version
            for version in log_entry.versions
        }
        if log_entry_version_id not in versions_by_id:
            return {
                "message": f"version {log_entry_version_id} for log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return instrument_log_entry_version_to_json(versions_by_id[log_entry_version_id])


class InstrumentLogEntryFileAttachments(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return [
            file_attachment_to_json(file_attachment)
            for file_attachment in log_entry.file_attachments
        ]


class InstrumentLogEntryFileAttachment(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int, file_attachment_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        try:
            file_attachment = get_instrument_log_file_attachment(file_attachment_id)
            if file_attachment.log_entry_id != log_entry_id:
                raise errors.InstrumentLogFileAttachmentDoesNotExistError()
        except errors.InstrumentLogFileAttachmentDoesNotExistError:
            return {
                "message": f"file attachment {file_attachment_id} for log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return file_attachment_to_json(file_attachment)


class InstrumentLogEntryObjectAttachments(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return [
            object_attachment_to_json(object_attachment)
            for object_attachment in log_entry.object_attachments
        ]


class InstrumentLogEntryObjectAttachment(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int, object_attachment_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        try:
            object_attachment = get_instrument_log_object_attachment(object_attachment_id)
            if object_attachment.log_entry_id != log_entry_id:
                raise errors.InstrumentLogObjectAttachmentDoesNotExistError()
        except errors.InstrumentLogObjectAttachmentDoesNotExistError:
            return {
                "message": f"object attachment {object_attachment_id} for log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return object_attachment_to_json(object_attachment)


class InstrumentLogCategories(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log categories for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        categories = get_instrument_log_categories(instrument_id)
        return [
            category_to_json(category)
            for category in categories
        ]


class InstrumentLogCategory(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, category_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log categories for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        categories = get_instrument_log_categories(instrument_id)
        for category in categories:
            if category.id == category_id:
                return category_to_json(category)
        return {
            "message": f"log category {category_id} for instrument {instrument_id} does not exist"
        }, 404
