# coding: utf-8
"""

"""
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from . import Objects
from .utils import Model


class ObjectPublication(Model):
    __tablename__ = 'object_publications'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    doi: Mapped[str] = db.Column(db.String, nullable=False)
    title: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    object_name: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ObjectPublication"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, doi),
    )
