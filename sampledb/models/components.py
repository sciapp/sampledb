# coding: utf-8
"""

"""
import datetime
import typing

from sqlalchemy.orm import Query, Mapped

from .. import db
from .utils import Model


class Component(Model):
    __tablename__ = 'components'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    address: Mapped[typing.Optional[str]] = db.Column(db.Text, nullable=True)
    uuid: Mapped[str] = db.Column(db.Text, nullable=False, unique=True)
    name: Mapped[typing.Optional[str]] = db.Column(db.Text, nullable=True, unique=True)
    description: Mapped[str] = db.Column(db.Text, nullable=False, default='')
    last_sync_timestamp: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.DateTime, nullable=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Component"]]

    def __init__(
            self,
            uuid: str,
            name: typing.Optional[str] = None,
            description: typing.Optional[str] = '',
            address: typing.Optional[str] = None,
            last_sync_timestamp: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            address=address,
            uuid=uuid,
            name=name,
            description=description,
            last_sync_timestamp=last_sync_timestamp
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, address={self.address}, uuid={self.uuid}, name={self.name}, description={self.description})>'
