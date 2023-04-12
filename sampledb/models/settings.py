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

from sqlalchemy.orm import Mapped, Query

from .. import db
from .users import User
from .utils import Model


class Settings(Model):
    __tablename__ = 'settings'

    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Settings"]]

    def __init__(
            self,
            user_id: int,
            data: typing.Dict[str, typing.Any]
    ) -> None:
        super().__init__(
            user_id=user_id,
            data=data
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(user_id={self.user_id}, data={self.data})>'
