# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from .objects import Objects


class File(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    data = db.Column(db.JSON, nullable=True)
    binary_data = db.deferred(db.Column(db.LargeBinary, nullable=True))
    uploader = db.relationship('User')

    def __init__(
            self,
            file_id: int,
            object_id: int,
            user_id: int,
            utc_datetime: typing.Optional[datetime.datetime] = None,
            data: typing.Optional[typing.Dict[str, typing.Any]] = None,
            binary_data: typing.Optional[bytes] = None
    ):
        self.id = file_id
        self.object_id = object_id
        self.user_id = user_id
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.data = data
        self.binary_data = binary_data

    def __repr__(self):
        return '<{0}(id={1.id}, object_id={1.object_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, data="{1.data}")>'.format(type(self).__name__, self)
