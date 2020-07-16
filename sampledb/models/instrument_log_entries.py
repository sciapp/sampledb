# coding: utf-8
"""
Model for instrument log entries

This should not to be confused with internal logging like the object log
"""

import datetime
import typing

from .. import db
from .instruments import Instrument
from .objects import Objects


class InstrumentLogEntry(db.Model):
    __tablename__ = 'instrument_log_entries'

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey(Instrument.id), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    author = db.relationship('User')

    def __init__(
            self,
            instrument_id: int,
            user_id: int,
            content: str,
            utc_datetime: typing.Optional[datetime.datetime] = None
    ):
        self.instrument_id = instrument_id
        self.user_id = user_id
        self.content = content
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self):
        return '<{0}(id={1.id}, instrument_id={1.instrument_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, content="{1.content}")>'.format(type(self).__name__, self)


class InstrumentLogFileAttachment(db.Model):
    __tablename__ = 'instrument_log_file_attachments'

    id = db.Column(db.Integer, primary_key=True)
    log_entry_id = db.Column(db.Integer, db.ForeignKey(InstrumentLogEntry.id), nullable=False)
    file_name = db.Column(db.String, nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)

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

    def __init__(self, log_entry_id: int, object_id: int):
        self.log_entry_id = log_entry_id
        self.object_id = object_id

    def __repr__(self):
        return '<{0}(id={1.id}, log_entry_id={1.log_entry_id}, object_id={1.object_id})>'.format(type(self).__name__, self)
