# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from .actions import SciCatExportType
from .objects import Objects
from .users import User


class SciCatExport(db.Model):  # type: ignore
    __tablename__ = 'scicat_exports'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    scicat_url = db.Column(db.String, nullable=False)
    scicat_pid = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    type = db.Column(db.Enum(SciCatExportType), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)

    def __init__(
            self,
            object_id: int,
            scicat_url: str,
            scicat_pid: str,
            user_id: int,
            type: SciCatExportType,
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        self.object_id = object_id
        self.scicat_url = scicat_url
        self.scicat_pid = scicat_pid
        self.user_id = user_id
        self.type = type
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self) -> str:
        return '<{0}(object_id={1.object_id}, scicat_url={1.scicat_url})>'.format(type(self).__name__, self)
