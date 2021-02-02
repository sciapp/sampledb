# coding: utf-8
"""

"""

import enum
import datetime

from .. import db
from .objects import Objects

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@enum.unique
class ObjectLogEntryType(enum.Enum):
    OTHER = 0
    CREATE_OBJECT = 1
    EDIT_OBJECT = 2
    RESTORE_OBJECT_VERSION = 3
    USE_OBJECT_IN_MEASUREMENT = 4
    POST_COMMENT = 5
    UPLOAD_FILE = 6
    USE_OBJECT_IN_SAMPLE_CREATION = 7
    CREATE_BATCH = 8
    ASSIGN_LOCATION = 9
    LINK_PUBLICATION = 10
    REFERENCE_OBJECT_IN_METADATA = 11
    EXPORT_TO_DATAVERSE = 12
    LINK_PROJECT = 13
    UNLINK_PROJECT = 14


class ObjectLogEntry(db.Model):
    __tablename__ = 'object_log_entries'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(ObjectLogEntryType), nullable=False)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User')

    def __init__(self, type, object_id, user_id, data, utc_datetime=None):
        self.type = type
        self.object_id = object_id
        self.user_id = user_id
        self.data = data
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self):
        return '<{0}(id={1.id}, type={1.type}, object_id={1.object_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, data={1.data})>'.format(type(self).__name__, self)
