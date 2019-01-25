# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from .objects import Objects


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    author = db.relationship('User')

    def __init__(self, object_id: int, user_id: int, content: str, utc_datetime: typing.Optional[datetime.datetime] = None):
        self.object_id = object_id
        self.user_id = user_id
        self.content = content
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self):
        return '<{0}(id={1.id}, object_id={1.object_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, content="{1.content}")>'.format(type(self).__name__, self)
