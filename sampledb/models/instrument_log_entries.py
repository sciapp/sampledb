# coding: utf-8
"""
Model for instrument log entries

This should not to be confused with internal logging like the object log.
"""

import enum
import datetime
import typing

from .. import db
from .instruments import Instrument
from .objects import Objects


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


class InstrumentLogCategory(db.Model):
    __tablename__ = 'instrument_log_categories'

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey(Instrument.id), nullable=False)
    title = db.Column(db.String, nullable=False)
    theme = db.Column(db.Enum(InstrumentLogCategoryTheme), nullable=False)

    def __init__(self, instrument_id: int, title: str, theme: InstrumentLogCategoryTheme):
        self.instrument_id = instrument_id
        self.title = title
        self.theme = theme

    def __repr__(self):
        return f'<{type(self).__name__}(id={self.id}, instrument_id={self.instrument_id}, title="{self.title}", theme={self.theme.name.lower()})>'


class InstrumentLogEntry(db.Model):
    __tablename__ = 'instrument_log_entries'

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey(Instrument.id), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author = db.relationship('User')

    def __init__(
            self,
            instrument_id: int,
            user_id: int
    ):
        self.instrument_id = instrument_id
        self.user_id = user_id

    def __repr__(self):
        return '<{0}(id={1.id}, instrument_id={1.instrument_id}, user_id={1.user_id})>'.format(type(self).__name__, self)


class InstrumentLogEntryVersion(db.Model):
    __tablename__ = 'instrument_log_entry_versions'

    log_entry_id = db.Column(db.Integer, db.ForeignKey(InstrumentLogEntry.id), primary_key=True)
    version_id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    content_is_markdown = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    event_utc_datetime = db.Column(db.DateTime, nullable=True)
    categories = db.relationship('InstrumentLogCategory', secondary=instrument_log_entry_category_association_table)
    log_entry = db.relationship(InstrumentLogEntry, backref='versions')

    def __init__(
            self,
            log_entry_id: int,
            version_id: int,
            content: str,
            utc_datetime: typing.Optional[datetime.datetime] = None,
            content_is_markdown: bool = False,
            event_utc_datetime: typing.Optional[datetime.datetime] = None
    ):
        self.log_entry_id = log_entry_id
        self.version_id = version_id
        self.content = content
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.content_is_markdown = content_is_markdown
        self.event_utc_datetime = event_utc_datetime

    def __repr__(self):
        return '<{0}(log_entry_id={1.log_entry_id}, version_id={1.version_id},  utc_datetime={1.utc_datetime}, content="{1.content}")>'.format(type(self).__name__, self)


class InstrumentLogFileAttachment(db.Model):
    __tablename__ = 'instrument_log_file_attachments'

    id = db.Column(db.Integer, primary_key=True)
    log_entry_id = db.Column(db.Integer, db.ForeignKey(InstrumentLogEntry.id), nullable=False)
    file_name = db.Column(db.String, nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, log_entry_id: int, file_name: str, content: bytes):
        self.log_entry_id = log_entry_id
        self.file_name = file_name
        self.content = content

    def __repr__(self):
        return '<{0}(id={1.id}, log_entry_id={1.log_entry_id}, file_name="{1.file_name}")>'.format(type(self).__name__, self)


class InstrumentLogObjectAttachment(db.Model):
    __tablename__ = 'instrument_log_object_attachments'

    id = db.Column(db.Integer, primary_key=True)
    log_entry_id = db.Column(db.Integer, db.ForeignKey(InstrumentLogEntry.id), nullable=False)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, log_entry_id: int, object_id: int):
        self.log_entry_id = log_entry_id
        self.object_id = object_id

    def __repr__(self):
        return '<{0}(id={1.id}, log_entry_id={1.log_entry_id}, object_id={1.object_id})>'.format(type(self).__name__, self)
