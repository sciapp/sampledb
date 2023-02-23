# coding: utf-8
"""
Models for users' favorite actions and instruments.
"""
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .utils import Model


class FavoriteAction(Model):
    __tablename__ = 'favorite_actions'

    action_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("actions.id"), primary_key=True)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FavoriteAction"]]


class FavoriteInstrument(Model):
    __tablename__ = 'favorite_instruments'

    instrument_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("instruments.id"), primary_key=True)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FavoriteInstrument"]]
