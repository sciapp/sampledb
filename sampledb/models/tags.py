# coding: utf-8
"""

"""
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .utils import Model


class Tag(Model):
    __tablename__ = 'tags'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String, unique=True, nullable=False)
    uses: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Tag"]]
