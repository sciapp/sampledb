# coding: utf-8
"""

"""

import enum
import datetime
import typing

from .. import db

from .users import User


@enum.unique
class NotificationType(enum.Enum):
    OTHER = 0


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(NotificationType), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    was_read = db.Column(db.Boolean, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)

    def __init__(self, type: NotificationType, user_id: int, data: typing.Dict[str, typing.Any], utc_datetime: typing.Optional[datetime.datetime]=None):
        self.type = type
        self.user_id = user_id
        self.data = data
        self.was_read = False
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self):
        return '<{0}(id={1.id}, type={1.type}, data={1.data})>'.format(type(self).__name__, self)
