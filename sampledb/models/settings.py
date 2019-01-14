# coding: utf-8
"""
Settings model.

To avoid creating a new table for each single type of user settings, the
Settings model allows storing all miscellaneous preferences for a user in
JSON format.
Some types of settings, e.g. notification settings, are complex enough to
justify custom models, while others are very simple, e.g. a single boolean
value or number, and can be stored using this model.
"""

import typing

from .. import db
from .users import User


class Settings(db.Model):
    __tablename__ = 'settings'

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    data = db.Column(db.JSON, nullable=False)

    def __init__(self, user_id: int, data: typing.Dict[str, typing.Any]) -> None:
        self.user_id = user_id
        self.data = data

    def __repr__(self) -> str:
        return '<{0}(user_id={1.user_id}, data={1.data})>'.format(type(self).__name__, self)
