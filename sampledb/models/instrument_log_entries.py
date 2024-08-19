# coding: utf-8
"""
Model for instrument log entries

This should not to be confused with internal logging like the object log.
"""

import enum
import datetime
import typing

from sqlalchemy.orm import relationship, Mapped, Query

from .. import db
from .instruments import Instrument
from .objects import Objects
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User


instrument_log_entry_category_association_table = db.Table(
    'instrument_log_entry_version_category_associations',
    db.metadata,
    db.Column('log_entry_id', db.Integer),
    db.Column('log_entry_version_id', db.Integer),
    db.Column('category_id', db.Integer, db.ForeignKey('instrument_log_categories.id', ondelete="CASCADE")),
    db.ForeignKeyConstraint(
        ['log_entry_id', 'log_entry_version_id'],
        ['instrument_log_entry_versions.log_entry_id', 'instrument_log_entry_versions.version_id']
    )
)


@enum.unique
class InstrumentLogCategoryTheme(enum.Enum):
    GRAY = 0
    BLUE = 1
    GREEN = 2
    YELLOW = 3
    RED = 4


class InstrumentLogCategory(Model):
    __tablename__ = 'instrument_log_categories'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    instrument_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Instrument.id), nullable=False)
    title: Mapped[str] = db.Column(db.String, nullable=False)
    theme: Mapped[InstrumentLogCategoryTheme] = db.Column(db.Enum(InstrumentLogCategoryTheme), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InstrumentLogCategory"]]

    def __init__(
            self,
            instrument_id: int,
            title: str,
            theme: InstrumentLogCategoryTheme
    ) -> None:
        super().__init__(
            instrument_id=instrument_id,
            title=title,
            theme=theme
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, instrument_id={self.instrument_id}, title="{self.title}", theme={self.theme.name.lower()})>'


class InstrumentLogEntry(Model):
    __tablename__ = 'instrument_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    instrument_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Instrument.id), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author: Mapped['User'] = relationship('User')
    versions: Mapped[typing.List['InstrumentLogEntryVersion']] = relationship('InstrumentLogEntryVersion', lazy="joined")

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InstrumentLogEntry"]]

    def __init__(
            self,
            instrument_id: int,
            user_id: int
    ) -> None:
        super().__init__(
            instrument_id=instrument_id,
            user_id=user_id
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, instrument_id={self.instrument_id}, user_id={self.user_id})>'


class InstrumentLogEntryVersion(Model):
    __tablename__ = 'instrument_log_entry_versions'

    log_entry_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(InstrumentLogEntry.id), primary_key=True)
    version_id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    content: Mapped[str] = db.Column(db.Text, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    content_is_markdown: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    event_utc_datetime: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    categories: Mapped[typing.List[InstrumentLogCategory]] = relationship('InstrumentLogCategory', secondary=instrument_log_entry_category_association_table, lazy="joined")
    log_entry: Mapped[InstrumentLogEntry] = relationship(InstrumentLogEntry, back_populates='versions')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InstrumentLogEntryVersion"]]

    def __init__(
            self,
            log_entry_id: int,
            version_id: int,
            content: str,
            utc_datetime: typing.Optional[datetime.datetime] = None,
            content_is_markdown: bool = False,
            event_utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            log_entry_id=log_entry_id,
            version_id=version_id,
            content=content,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            content_is_markdown=content_is_markdown,
            event_utc_datetime=event_utc_datetime
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(log_entry_id={self.log_entry_id}, version_id={self.version_id},  utc_datetime={self.utc_datetime}, content="{self.content}")>'


class InstrumentLogFileAttachment(Model):
    __tablename__ = 'instrument_log_file_attachments'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    log_entry_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(InstrumentLogEntry.id), nullable=False)
    file_name: Mapped[str] = db.Column(db.String, nullable=False)
    content: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)
    is_hidden: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    image_info: Mapped['InstrumentLogFileAttachmentImageInfo'] = relationship('InstrumentLogFileAttachmentImageInfo', backref='file_attachment', uselist=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InstrumentLogFileAttachment"]]

    def __init__(
            self,
            log_entry_id: int,
            file_name: str,
            content: bytes
    ) -> None:
        super().__init__(
            log_entry_id=log_entry_id,
            file_name=file_name,
            content=content
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, log_entry_id={self.log_entry_id}, file_name="{self.file_name}")>'


class InstrumentLogFileAttachmentImageInfo(Model):
    __tablename__ = 'instrument_log_file_attachment_image_infos'

    file_attachment_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(InstrumentLogFileAttachment.id), primary_key=True)
    thumbnail_content: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)
    thumbnail_mime_type: Mapped[str] = db.Column(db.String, nullable=False)
    width: Mapped[int] = db.Column(db.Integer, nullable=False)
    height: Mapped[int] = db.Column(db.Integer, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InstrumentLogFileAttachmentImageInfo"]]


class InstrumentLogObjectAttachment(Model):
    __tablename__ = 'instrument_log_object_attachments'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    log_entry_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(InstrumentLogEntry.id), nullable=False)
    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    is_hidden: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InstrumentLogObjectAttachment"]]

    def __init__(
            self,
            log_entry_id: int,
            object_id: int
    ) -> None:
        super().__init__(
            log_entry_id=log_entry_id,
            object_id=object_id
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, log_entry_id={self.log_entry_id}, object_id={self.object_id})>'
