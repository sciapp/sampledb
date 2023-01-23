# coding: utf-8
"""

"""
import datetime
import typing

from .. import db


class Component(db.Model):  # type: ignore
    __tablename__ = 'components'

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.Text, nullable=True)
    uuid = db.Column(db.Text, nullable=False, unique=True)
    name = db.Column(db.Text, nullable=True, unique=True)
    description = db.Column(db.Text, nullable=False, default='')
    last_sync_timestamp = db.Column(db.DateTime, nullable=True)

    def __init__(
            self,
            uuid: str,
            name: typing.Optional[str] = None,
            description: typing.Optional[str] = '',
            address: typing.Optional[str] = None,
            last_sync_timestamp: typing.Optional[datetime.datetime] = None
    ) -> None:
        self.address = address
        self.uuid = uuid
        self.name = name
        self.description = description
        self.last_sync_timestamp = last_sync_timestamp

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, address={1.address}, uuid={1.uuid}, name={1.name}, description={1.description})>'.format(type(self).__name__, self)
