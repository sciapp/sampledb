# coding: utf-8
"""

"""

import enum
import datetime

from .. import db
from .files import File

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@enum.unique
class FileLogEntryType(enum.Enum):
    OTHER = 0
    EDIT_TITLE = 1
    EDIT_DESCRIPTION = 2
    HIDE_FILE = 3
    UNHIDE_FILE = 4


class FileLogEntry(db.Model):
    __tablename__ = 'file_log_entries'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(FileLogEntryType), nullable=False)
    object_id = db.Column(db.Integer, nullable=False)
    file_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User')

    __table_args__ = (db.ForeignKeyConstraint([object_id, file_id], [File.object_id, File.id]), {})

    def __init__(self, object_id, file_id, user_id, type, data, utc_datetime=None):
        self.object_id = object_id
        self.file_id = file_id
        self.user_id = user_id
        self.type = type
        self.data = data
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self):
        return '<{0}(id={1.id}, type={1.type}, file_id={1.file_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, data={1.data})>'.format(type(self).__name__, self)
