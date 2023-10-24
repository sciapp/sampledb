# coding: utf-8
"""

"""

import enum
import datetime
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .objects import Objects
from .users import User
from .utils import Model


@enum.unique
class DataverseExportStatus(enum.Enum):
    TASK_CREATED = 0
    EXPORT_FINISHED = 1


class DataverseExport(Model):
    __tablename__ = 'dataverse_exports'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    dataverse_url: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    status: Mapped[DataverseExportStatus] = db.Column(db.Enum(DataverseExportStatus), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["DataverseExport"]]

    def __init__(
            self,
            object_id: int,
            dataverse_url: typing.Optional[str],
            user_id: int,
            status: DataverseExportStatus,
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            object_id=object_id,
            dataverse_url=dataverse_url,
            user_id=user_id,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            status=status
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(object_id={self.object_id}, dataverse_url={self.dataverse_url})>'
