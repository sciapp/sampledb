import base64
import datetime
import typing
from contextlib import suppress
from dataclasses import dataclass
from http import HTTPStatus

import flask
import pytz
from pydantic import BaseModel, NonNegativeInt, Strict, ValidationInfo, constr, model_validator, Field, AwareDatetime
from pydantic_core import PydanticCustomError

from .authentication import multi_auth
from .instruments import InstrumentNotFoundModel
from ..utils import Resource
from ...logic.instruments import get_instrument
from ...logic.instrument_log_entries import InstrumentLogEntry as LogicInstrumentLogEntry, InstrumentLogFileAttachment, InstrumentLogObjectAttachment, get_instrument_log_entries, get_instrument_log_entry, get_instrument_log_file_attachment, get_instrument_log_object_attachment, get_instrument_log_categories, create_instrument_log_entry, create_instrument_log_file_attachment, create_instrument_log_object_attachment, update_instrument_log_entry, hide_instrument_log_object_attachment, hide_instrument_log_file_attachment
from ...logic import errors, instrument_log_entries
from ...logic.object_permissions import get_user_object_permissions
from ...models import Permissions
from .utils.validation import Base64Encoded, ModelWithDefaultsFromValidationInfo, is_valid, populate_missing_or_expect_from_validation_info, generate_example
from .utils.responses import make_response, ErrorDetailsModel, CreatedResponseModel, PaginatedSequence, \
    PaginationQueryModel
from .utils.openapi import method

MAX_FILE_NAME_LENGTH = 256


@dataclass(frozen=True, slots=True)
class _ValidationContext:
    log_entry: LogicInstrumentLogEntry | None
    existing_category_ids: frozenset[int]

    @property
    def existing_file_attachments(self) -> list[InstrumentLogFileAttachment]:
        assert self.log_entry is not None
        return [fa for fa in self.log_entry.file_attachments if not fa.is_hidden]

    @property
    def existing_object_attachments(self) -> list[InstrumentLogObjectAttachment]:
        assert self.log_entry is not None
        return [oa for oa in self.log_entry.object_attachments if not oa.is_hidden]

    @classmethod
    def from_path_without_log_entry(cls, path: InstrumentLogEntries.PathModel) -> typing.Self:
        try:
            existing_category_ids = frozenset(category.id for category in get_instrument_log_categories(path.instrument_id))
        except errors.InstrumentDoesNotExistError:
            flask.abort(make_response(
                result=InstrumentNotFoundModel(detail=f"Instrument #{path.instrument_id} does not exist."),
                default_status_code=InstrumentNotFoundModel.STATUS,
                return_type_hint=None
            ))
        return cls(
            log_entry=None,
            existing_category_ids=existing_category_ids
        )

    @classmethod
    def from_path_with_log_entry(cls, path: InstrumentLogEntryVersions.PathModel) -> typing.Self:
        try:
            existing_category_ids = frozenset(category.id for category in get_instrument_log_categories(path.instrument_id))
        except errors.InstrumentDoesNotExistError:
            flask.abort(make_response(
                result=InstrumentNotFoundModel(detail=f"Instrument #{path.instrument_id} does not exist."),
                default_status_code=InstrumentNotFoundModel.STATUS,
                return_type_hint=None
            ))
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            flask.abort(make_response(
                result=InstrumentLogEntryNotFoundModel(detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."),
                default_status_code=InstrumentLogEntryNotFoundModel.STATUS,
                return_type_hint=None
            ))
        return cls(
            log_entry=log_entry,
            existing_category_ids=existing_category_ids,
        )


# pyflakes doesn't like string literals in type annotations that don't correspond to a Python identifier
_base64_content = "base64_content"


class _FileAttachment(BaseModel):
    if typing.TYPE_CHECKING:
        file_name: str
        content: bytes
    else:
        file_name: constr(strip_whitespace=True, min_length=1, max_length=MAX_FILE_NAME_LENGTH) = Field(description="the name of the attached file", examples=["example.txt"])
        content: Base64Encoded(_base64_content) = Field(description="the base64 encoded content of the attached file", examples=["ZXhhbXBsZQ=="])


class _ObjectAttachment(BaseModel):
    object_id: typing.Annotated[NonNegativeInt, Strict()] = Field(description="the ID of the attached object", examples=[1])

    @model_validator(mode="after")
    def check_object_exists(self) -> typing.Self:
        try:
            permissions = get_user_object_permissions(self.object_id, flask.g.user.id)
            if Permissions.READ not in permissions:
                raise errors.ObjectDoesNotExistError()
            return self
        except errors.ObjectDoesNotExistError:
            raise PydanticCustomError("no_such_object", "Object should exist")


class _BaseInstrumentLogEntry(ModelWithDefaultsFromValidationInfo):
    content: str | None = Field(description="the content for the instrument log entry", examples=["This is an instrument log entry."])
    content_is_markdown: bool = Field(False, description="whether the content for the instrument log entry is formatted in Markdown", examples=[False])
    category_ids: list[
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
    ] = Field([], description="the IDs of the categories for the instrument log entry", examples=[[1, 2, 4]])
    event_utc_datetime: typing.Annotated[
        AwareDatetime,
        is_valid(
            lambda v, i: abs(v - datetime.datetime.now(tz=pytz.utc)) <= datetime.timedelta(days=365_242),
            lambda i: PydanticCustomError("datetime_range", "Timestamp should not be more than 1000 years before or after the current date"),
        ),
    ] | None = Field(None, description="the ISO-formatted datetime in UTC of the event described in the instrument log entry", examples=["2026-01-02T03:04:05.678910Z"])


_ObjectAttachments = typing.Annotated[
    list[_ObjectAttachment],
    is_valid(
        lambda v, i: len({x.object_id for x in v}) == len(v),
        lambda i: PydanticCustomError("unique", "Object should only be attached once"),
    ),
]


class InstrumentLogCategoryModel(BaseModel):
    category_id: int = Field(description="the ID of the category", examples=[1])
    title: str = Field(description="the title of the category", examples=[1])

    @classmethod
    def from_category(cls, category: instrument_log_entries.InstrumentLogCategory) -> typing.Self:
        return cls(
            category_id=category.id,
            title=category.title
        )


class InstrumentLogEntryVersionModel(BaseModel):
    log_entry_id: int = Field(description="the ID of the instrument log entry the version belongs to", examples=[1])
    version_id: int = Field(description="the ID of the instrument log entry version", examples=[1])
    utc_datetime: AwareDatetime = Field(description="the ISO-formatted datetime in UTC when the instrument log entry version was created", examples=["2026-01-02T03:04:05.678910Z"])
    content: str = Field(description="the content of the instrument log entry", examples=["This is a log entry."])
    categories: list[InstrumentLogCategoryModel] = Field(description="the categories of the instrument log entry", examples=[[generate_example(InstrumentLogCategoryModel)]])
    event_utc_datetime: AwareDatetime | None = Field(description="the ISO-formatted datetime in UTC of the event described in the instrument log entry", examples=["2026-01-02T03:04:05.678910Z"])
    content_is_markdown: bool = Field(description="whether the content of the instrument log entry is formatted in Markdown", examples=[False])

    @classmethod
    def from_instrument_log_entry_version(cls, instrument_log_entry_version: instrument_log_entries.InstrumentLogEntryVersion) -> typing.Self:
        return cls(
            log_entry_id=instrument_log_entry_version.log_entry_id,
            version_id=instrument_log_entry_version.version_id,
            utc_datetime=instrument_log_entry_version.utc_datetime,
            content=instrument_log_entry_version.content,
            categories=[
                InstrumentLogCategoryModel.from_category(category)
                for category in instrument_log_entry_version.categories
            ],
            event_utc_datetime=instrument_log_entry_version.event_utc_datetime if instrument_log_entry_version.event_utc_datetime is not None else None,
            content_is_markdown=instrument_log_entry_version.content_is_markdown,
        )


class InstrumentLogEntryModel(BaseModel):
    log_entry_id: int = Field(description="the ID of the instrument log entry", examples=[1])
    author: int = Field(description="the ID of the user who created the instrument log entry", examples=[1])
    versions: list[InstrumentLogEntryVersionModel] = Field(description="the versions of the instrument log entry", examples=[[generate_example(InstrumentLogEntryVersionModel)]])

    @classmethod
    def from_instrument_log_entry(cls, instrument_log_entry: instrument_log_entries.InstrumentLogEntry) -> typing.Self:
        return cls(
            log_entry_id=instrument_log_entry.id,
            author=instrument_log_entry.user_id,
            versions=[
                InstrumentLogEntryVersionModel.from_instrument_log_entry_version(version)
                for version in instrument_log_entry.versions
            ]
        )


class InstrumentLogFileAttachmentModel(BaseModel):
    file_attachment_id: int = Field(description="the ID of the file attachment", examples=[1])
    file_name: str | None = Field(description="the name of the attached file", examples=["example.txt"])
    base64_content: str | None = Field(description="the base64 encoded content of the attached file", examples=["ZXhhbXBsZQ=="])
    is_hidden: bool = Field(description="whether the file attachment is hidden", examples=[False])

    @classmethod
    def from_instrument_log_file_attachment(cls, file_attachment: instrument_log_entries.InstrumentLogFileAttachment) -> typing.Self:
        return cls(
            file_attachment_id=file_attachment.id,
            file_name=file_attachment.file_name if not file_attachment.is_hidden else None,
            base64_content=base64.b64encode(file_attachment.content).decode('ascii') if not file_attachment.is_hidden else None,
            is_hidden=file_attachment.is_hidden
        )


class InstrumentLogObjectAttachmentModel(BaseModel):
    object_attachment_id: int = Field(description="the ID of the object attachment", examples=[1])
    object_id: int | None = Field(description="the ID of the attached object", examples=[1])
    is_hidden: bool = Field(description="whether the object attachment is hidden", examples=[False])

    @classmethod
    def from_instrument_log_object_attachment(cls, object_attachment: instrument_log_entries.InstrumentLogObjectAttachment) -> typing.Self:
        return cls(
            object_attachment_id=object_attachment.id,
            object_id=object_attachment.object_id if not object_attachment.is_hidden else None,
            is_hidden=object_attachment.is_hidden
        )


class CreatingInstrumentLogEntriesForbiddenModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.FORBIDDEN
    TITLE: typing.ClassVar[str] = "Only instrument scientists may create instrument log entries."


class ViewingInstrumentLogEntriesForbiddenModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.FORBIDDEN
    TITLE: typing.ClassVar[str] = "Only instrument scientists may view instrument log entries."


class InstrumentLogEntryNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested instrument log entry does not exist."


class InstrumentLogEntryVersionNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested instrument log entry version does not exist."


class InstrumentLogFileAttachmentNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested instrument log file attachment does not exist."


class InstrumentLogObjectAttachmentNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested instrument log object attachment does not exist."


class InstrumentLogCategoryNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested instrument log category does not exist."


class InstrumentLogEntries(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])

    class RequestBodyModel(_BaseInstrumentLogEntry):
        file_attachments: list[_FileAttachment] = Field([], description="a list of file attachments", examples=[[]])
        object_attachments: _ObjectAttachments = Field([], description="a list of object attachments", examples=[[]])

        @model_validator(mode="after")
        def check_not_empty(self) -> typing.Self:
            if self.content or self.file_attachments or self.object_attachments:
                return self
            raise PydanticCustomError("log_entry_empty", "Log entry should contain content or an attachment")

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel, query: PaginationQueryModel) -> PaginatedSequence[InstrumentLogEntryModel] | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel:
        """
        List all log entries for an instrument.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        log_entries = get_instrument_log_entries(
            instrument_id=path.instrument_id,
            after_id=query.previous_id,
            limit=query.limit,
            sort_by='id',
        )
        return PaginatedSequence(
            items=[
                InstrumentLogEntryModel.from_instrument_log_entry(log_entry)
                for log_entry in log_entries
            ],
            query=query,
            path=path,
            id_getter=lambda log_entry: log_entry.log_entry_id,
        )

    @multi_auth.login_required
    @method(request_body_context_builder=_ValidationContext.from_path_without_log_entry)
    def post(self, path: PathModel, request_body: RequestBodyModel) -> CreatedResponseModel | InstrumentNotFoundModel | CreatingInstrumentLogEntriesForbiddenModel:
        """
        Create a new instrument log entry.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_create_log_entries and flask.g.user not in instrument.responsible_users:
            return CreatingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may create log entries for instrument #{path.instrument_id}."
            )

        log_entry = create_instrument_log_entry(
            instrument_id=instrument.id,
            user_id=flask.g.user.id,
            content=request_body.content or "",
            content_is_markdown=request_body.content_is_markdown,
            category_ids=request_body.category_ids,
            event_utc_datetime=request_body.event_utc_datetime,
        )

        for file_attachment in request_body.file_attachments:
            create_instrument_log_file_attachment(
                instrument_log_entry_id=log_entry.id,
                file_name=file_attachment.file_name,
                content=file_attachment.content,
            )

        for object_attachment in request_body.object_attachments:
            create_instrument_log_object_attachment(
                instrument_log_entry_id=log_entry.id,
                object_id=object_attachment.object_id,
            )

        return CreatedResponseModel(
            location=flask.url_for(
                '.instrument_log_entry',
                instrument_id=path.instrument_id,
                log_entry_id=log_entry.id,
                _external=True
            )
        )


class InstrumentLogEntry(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])
        log_entry_id: int = Field(description="the ID of an existing log entry for this instrument", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> InstrumentLogEntryModel | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogEntryNotFoundModel:
        """
        Get an instrument log entry.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return InstrumentLogEntryNotFoundModel(
                detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        return InstrumentLogEntryModel.from_instrument_log_entry(log_entry)


class InstrumentLogEntryVersions(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])
        log_entry_id: int = Field(description="the ID of an existing log entry for this instrument", examples=[1])

    class RequestBodyModel(_BaseInstrumentLogEntry):
        version_id: typing.Annotated[int, populate_missing_or_expect_from_validation_info(lambda i: len(i.context.log_entry.versions) + 1)] = Field(description="the ID for the new version of the instrument log entry, must be the current version_id + 1", examples=[1])
        log_entry_id: typing.Annotated[int, populate_missing_or_expect_from_validation_info(lambda i: i.context.log_entry.id)] = Field(description="the ID of an existing instrument log entry to update", examples=[1])
        file_attachments: list[_FileAttachment] | None = Field(None, description="the file attachments for the new instrument log entry version", examples=[[{"file_name": "example.txt", "base64_content": "ZXhhbXBsZQ=="}]])
        object_attachments: _ObjectAttachments | None = Field(None, description="the object attachments for the new instrument log entry version", examples=[[{"object_id": 1}]])

        @model_validator(mode="after")
        def check_not_empty(self, info: ValidationInfo[_ValidationContext]) -> typing.Self:
            file_attachments = info.context.existing_file_attachments if self.file_attachments is None else self.file_attachments
            object_attachments = info.context.existing_object_attachments if self.object_attachments is None else self.object_attachments
            if self.content or file_attachments or object_attachments:
                return self
            raise PydanticCustomError("log_entry_empty", "Log entry should contain content or an attachment")

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel, query: PaginationQueryModel) -> PaginatedSequence[InstrumentLogEntryVersionModel] | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogEntryNotFoundModel:
        """
        List all versions of an instrument log entry.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return InstrumentLogEntryNotFoundModel(
                detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        return PaginatedSequence.apply_pagination(
            items=[
                InstrumentLogEntryVersionModel.from_instrument_log_entry_version(version)
                for version in log_entry.versions
            ],
            query=query,
            path=path,
            id_getter=lambda version: version.version_id,
        )

    @multi_auth.login_required
    @method(request_body_context_builder=_ValidationContext.from_path_with_log_entry)
    def post(self, path: PathModel, request_body: RequestBodyModel) -> CreatedResponseModel | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogEntryNotFoundModel:
        """
        Create a new version of an instrument log entry.
        """
        validation_context = _ValidationContext.from_path_with_log_entry(path)
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return InstrumentLogEntryNotFoundModel(
                detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        log_entry = update_instrument_log_entry(
            log_entry_id=log_entry.id,
            content=request_body.content or "",
            category_ids=request_body.category_ids,
            content_is_markdown=request_body.content_is_markdown,
            event_utc_datetime=request_body.event_utc_datetime,
        )
        if request_body.file_attachments is not None:
            new_file_attachments = {(file_attachment.file_name, file_attachment.content) for file_attachment in request_body.file_attachments}
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
        if request_body.object_attachments is not None:
            new_object_attachments = {object_attachment.object_id for object_attachment in request_body.object_attachments}
            for object_id in new_object_attachments.difference(oa.object_id for oa in log_entry.object_attachments):
                with suppress(errors.ObjectDoesNotExistError):
                    create_instrument_log_object_attachment(log_entry.id, object_id)
            for object_attachment in log_entry.object_attachments:
                should_be_hidden = object_attachment.object_id not in new_object_attachments
                if should_be_hidden != object_attachment.is_hidden:
                    hide_instrument_log_object_attachment(object_attachment.id, set_hidden=should_be_hidden)

        return CreatedResponseModel(
            location=flask.url_for(
                '.instrument_log_entry_version',
                instrument_id=path.instrument_id,
                log_entry_id=log_entry.id,
                log_entry_version_id=log_entry.versions[-1].version_id,
                _external=True
            )
        )


class InstrumentLogEntryVersion(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])
        log_entry_id: int = Field(description="the ID of an existing log entry for this instrument", examples=[1])
        log_entry_version_id: int = Field(description="the ID of an existing version of this instrument log entry", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> InstrumentLogEntryVersionModel | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogEntryNotFoundModel | InstrumentLogEntryVersionNotFoundModel:
        """
        Get a version of an instrument log entry.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return InstrumentLogEntryNotFoundModel(
                detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        versions_by_id = {
            version.version_id: version
            for version in log_entry.versions
        }
        if path.log_entry_version_id not in versions_by_id:
            return InstrumentLogEntryVersionNotFoundModel(
                detail=f"Version #{path.log_entry_version_id} for log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        return InstrumentLogEntryVersionModel.from_instrument_log_entry_version(versions_by_id[path.log_entry_version_id])


class InstrumentLogEntryFileAttachments(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])
        log_entry_id: int = Field(description="the ID of an existing log entry for this instrument", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel, query: PaginationQueryModel) -> PaginatedSequence[InstrumentLogFileAttachmentModel] | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogEntryNotFoundModel:
        """
        List all file attachments for an instrument log entry.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return InstrumentLogEntryNotFoundModel(
                detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        return PaginatedSequence.apply_pagination(
            items=[
                InstrumentLogFileAttachmentModel.from_instrument_log_file_attachment(file_attachment)
                for file_attachment in log_entry.file_attachments
            ],
            query=query,
            path=path,
            id_getter=lambda file_attachment: file_attachment.file_attachment_id,
        )


class InstrumentLogEntryFileAttachment(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])
        log_entry_id: int = Field(description="the ID of an existing log entry for this instrument", examples=[1])
        file_attachment_id: int = Field(description="the ID of an existing file attachment for this instrument log entry", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> InstrumentLogFileAttachmentModel | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogEntryNotFoundModel | InstrumentLogFileAttachmentNotFoundModel:
        """
        Get a file attachment for an instrument log entry.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return InstrumentLogEntryNotFoundModel(
                detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        try:
            file_attachment = get_instrument_log_file_attachment(path.file_attachment_id)
            if file_attachment.log_entry_id != path.log_entry_id:
                raise errors.InstrumentLogFileAttachmentDoesNotExistError()
        except errors.InstrumentLogFileAttachmentDoesNotExistError:
            return InstrumentLogFileAttachmentNotFoundModel(
                detail=f"File attachment #{path.file_attachment_id} for log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        return InstrumentLogFileAttachmentModel.from_instrument_log_file_attachment(file_attachment)


class InstrumentLogEntryObjectAttachments(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])
        log_entry_id: int = Field(description="the ID of an existing log entry for this instrument", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel, query: PaginationQueryModel) -> PaginatedSequence[InstrumentLogObjectAttachmentModel] | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogEntryNotFoundModel:
        """
        List all object attachments for an instrument log entry.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return InstrumentLogEntryNotFoundModel(
                detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        return PaginatedSequence.apply_pagination(
            items=[
                InstrumentLogObjectAttachmentModel.from_instrument_log_object_attachment(object_attachment)
                for object_attachment in log_entry.object_attachments
            ],
            query=query,
            path=path,
            id_getter=lambda object_attachment: object_attachment.object_attachment_id,
        )


class InstrumentLogEntryObjectAttachment(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])
        log_entry_id: int = Field(description="the ID of an existing log entry for this instrument", examples=[1])
        object_attachment_id: int = Field(description="the ID of an existing object attachment for this instrument log entry", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> InstrumentLogObjectAttachmentModel | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogEntryNotFoundModel | InstrumentLogObjectAttachmentNotFoundModel:
        """
        Get an object attachment for an instrument log entry.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        try:
            log_entry = get_instrument_log_entry(path.log_entry_id)
            if log_entry.instrument_id != path.instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return InstrumentLogEntryNotFoundModel(
                detail=f"Log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        try:
            object_attachment = get_instrument_log_object_attachment(path.object_attachment_id)
            if object_attachment.log_entry_id != path.log_entry_id:
                raise errors.InstrumentLogObjectAttachmentDoesNotExistError()
        except errors.InstrumentLogObjectAttachmentDoesNotExistError:
            return InstrumentLogObjectAttachmentNotFoundModel(
                detail=f"Object attachment #{path.object_attachment_id} for log entry #{path.log_entry_id} for instrument #{path.instrument_id} does not exist."
            )
        return InstrumentLogObjectAttachmentModel.from_instrument_log_object_attachment(object_attachment)


class InstrumentLogCategories(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel, query: PaginationQueryModel) -> PaginatedSequence[InstrumentLogCategoryModel] | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel:
        """
        List all log categories for an instrument.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        categories = get_instrument_log_categories(path.instrument_id)
        return PaginatedSequence.apply_pagination(
            items=[
                InstrumentLogCategoryModel.from_category(category)
                for category in categories
            ],
            query=query,
            path=path,
            id_getter=lambda category: category.category_id,
        )


class InstrumentLogCategory(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])
        category_id: int = Field(description="the ID of an existing log entry category for this instrument", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> InstrumentLogCategoryModel | InstrumentNotFoundModel | ViewingInstrumentLogEntriesForbiddenModel | InstrumentLogCategoryNotFoundModel:
        """
        Get an instrument log category.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(instrument_id=path.instrument_id)
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return ViewingInstrumentLogEntriesForbiddenModel(
                detail=f"Only instrument scientists may view log entries for instrument #{path.instrument_id}."
            )
        categories = get_instrument_log_categories(path.instrument_id)
        for category in categories:
            if category.id == path.category_id:
                return InstrumentLogCategoryModel.from_category(category)
        return InstrumentLogCategoryNotFoundModel(
            detail=f"Log category #{path.category_id} for instrument #{path.instrument_id} does not exist."
        )
