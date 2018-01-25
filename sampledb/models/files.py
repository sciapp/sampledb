# coding: utf-8
"""

"""

import datetime

from .. import db
from .objects import Objects


class File(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    original_file_name = db.Column(db.Text, nullable=False)
    uploader = db.relationship('User')

    def __init__(self, file_id: int, object_id: int, user_id: int, original_file_name: str, utc_datetime: datetime.datetime=None):
        self.id = file_id
        self.object_id = object_id
        self.user_id = user_id
        self.original_file_name = original_file_name
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self):
        return '<{0}(id={1.id}, object_id={1.object_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, original_file_name="{1.original_file_name}")>'.format(type(self).__name__, self)
