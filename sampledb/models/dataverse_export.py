# coding: utf-8
"""

"""

import enum
import datetime
import typing

from .. import db
from .objects import Objects
from .users import User


@enum.unique
class DataverseExportStatus(enum.Enum):
    TASK_CREATED = 0,
    EXPORT_FINISHED = 1,


class DataverseExport(db.Model):  # type: ignore
    __tablename__ = 'dataverse_exports'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    dataverse_url = db.Column(db.String, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(DataverseExportStatus), nullable=False)

    def __init__(
            self,
            object_id: int,
            dataverse_url: typing.Optional[str],
            user_id: int,
            status: DataverseExportStatus,
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        self.object_id = object_id
        self.dataverse_url = dataverse_url
        self.user_id = user_id
        self.status = status
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self) -> str:
        return '<{0}(object_id={1.object_id}, dataverse_url={1.dataverse_url})>'.format(type(self).__name__, self)
