# coding: utf-8
"""

"""

import datetime
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .actions import SciCatExportType
from .objects import Objects
from .users import User
from .utils import Model


class SciCatExport(Model):
    __tablename__ = 'scicat_exports'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    scicat_url: Mapped[str] = db.Column(db.String, nullable=False)
    scicat_pid: Mapped[str] = db.Column(db.String, nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    type: Mapped[SciCatExportType] = db.Column(db.Enum(SciCatExportType), nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["SciCatExport"]]

    def __init__(
            self,
            object_id: int,
            scicat_url: str,
            scicat_pid: str,
            user_id: int,
            type: SciCatExportType,
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            object_id=object_id,
            scicat_url=scicat_url,
            scicat_pid=scicat_pid,
            user_id=user_id,
            type=type,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(object_id={self.object_id}, scicat_url={self.scicat_url})>'
