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
    last_sync_timestamp: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    discoverable: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    fed_login_available: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Component"]]

    def __init__(
            self,
            uuid: str,
            name: typing.Optional[str] = None,
            description: typing.Optional[str] = '',
            address: typing.Optional[str] = None,
            last_sync_timestamp: typing.Optional[datetime.datetime] = None,
            discoverable: bool = True,
            fed_login_available: bool = False
    ) -> None:
        super().__init__(
            address=address,
            uuid=uuid,
            name=name,
            description=description,
            last_sync_timestamp=last_sync_timestamp,
            discoverable=discoverable,
            fed_login_available=fed_login_available
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, address={self.address}, uuid={self.uuid}, name={self.name}, description={self.description}, fed_login_available={self.fed_login_available})>'


class ComponentInfo(Model):
    __tablename__ = 'component_infos'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    uuid: Mapped[str] = db.Column(db.Text, nullable=False)
    source_uuid: Mapped[str] = db.Column(db.Text, nullable=False)
    address: Mapped[typing.Optional[str]] = db.Column(db.Text, nullable=True)
    name: Mapped[typing.Optional[str]] = db.Column(db.Text, nullable=True)
    discoverable: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    distance: Mapped[int] = db.Column(db.Integer, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ComponentInfo"]]

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, address={self.address}, uuid={self.uuid}, name={self.name}, source_uuid={self.source_uuid}, distance={self.distance})>'
