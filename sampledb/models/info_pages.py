# coding: utf-8
"""

"""
import datetime
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .utils import Model


class InfoPage(Model):
    __tablename__ = 'info_pages'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    title: Mapped[typing.Dict[str, str]] = db.Column(db.JSON, nullable=False)
    content: Mapped[typing.Dict[str, str]] = db.Column(db.JSON, nullable=False)
    endpoint: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    disabled: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)

    acknowledgements = db.relationship(
        'InfoPageAcknowledgement',
        back_populates='info_page',
        cascade='all, delete',
        passive_deletes=True
    )

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InfoPage"]]

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, title={self.title})>'


class InfoPageAcknowledgement(Model):
    __tablename__ = 'info_page_acknowledgements'

    info_page_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('info_pages.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    utc_datetime: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.DateTime, nullable=True)

    info_page = db.relationship(
        'InfoPage',
        back_populates='acknowledgements'
    )

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InfoPageAcknowledgement"]]

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(info_page_id={self.info_page_id}, user_id={self.user_id})>'
