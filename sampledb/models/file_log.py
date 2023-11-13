# coding: utf-8
"""

"""

import enum
import datetime
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .files import File
from .utils import Model

if typing.TYPE_CHECKING:
    from ..logic.users import User

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@enum.unique
class FileLogEntryType(enum.Enum):
    OTHER = 0
    EDIT_TITLE = 1
    EDIT_DESCRIPTION = 2
    HIDE_FILE = 3
    UNHIDE_FILE = 4
    EDIT_URL = 5


class FileLogEntry(Model):
    __tablename__ = 'file_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FileLogEntryType] = db.Column(db.Enum(FileLogEntryType), nullable=False)
    object_id: Mapped[int] = db.Column(db.Integer, nullable=False)
    file_id: Mapped[int] = db.Column(db.Integer, nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FileLogEntry"]]

    __table_args__ = (
        db.ForeignKeyConstraint([object_id, file_id], [File.object_id, File.id]),
    )

    def __init__(
            self,
            object_id: int,
            file_id: int,
            user_id: int,
            type: FileLogEntryType,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            object_id=object_id,
            file_id=file_id,
            user_id=user_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )
        self.user: typing.Optional['User'] = None

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, file_id={self.file_id}, user_id={self.user_id}, utc_datetime={self.utc_datetime}, data={self.data})>'
