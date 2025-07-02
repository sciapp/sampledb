# coding: utf-8
"""

"""

import enum
import datetime
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .objects import Objects
from .utils import Model

if typing.TYPE_CHECKING:
    from ..logic.users import User

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@enum.unique
class ObjectLogEntryType(enum.Enum):
    OTHER = 0
    CREATE_OBJECT = 1
    EDIT_OBJECT = 2
    RESTORE_OBJECT_VERSION = 3
    USE_OBJECT_IN_MEASUREMENT = 4
    POST_COMMENT = 5
    UPLOAD_FILE = 6
    USE_OBJECT_IN_SAMPLE_CREATION = 7
    CREATE_BATCH = 8
    ASSIGN_LOCATION = 9
    LINK_PUBLICATION = 10
    REFERENCE_OBJECT_IN_METADATA = 11
    EXPORT_TO_DATAVERSE = 12
    LINK_PROJECT = 13
    UNLINK_PROJECT = 14
    IMPORT_FROM_ELN_FILE = 15
    IMPORT_CONFLICTING_VERSION = 16
    SOLVE_VERSION_CONFLICT = 17


class ObjectLogEntry(Model):
    __tablename__ = 'object_log_entries'

    __table_args__ = (
        db.CheckConstraint("""
            (
                type != 'SOLVE_VERSION_CONFLICT' AND
                user_id IS NOT NULL
            ) OR (
                type = 'SOLVE_VERSION_CONFLICT' AND (
                    user_id IS NOT NULL OR
                    user_id IS NULL AND
                    ((data->>'automerged')::boolean) = true
                )
            )
        """, name="object_log_user_id_nullable"),
    )

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[ObjectLogEntryType] = db.Column(db.Enum(ObjectLogEntryType), nullable=False)
    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    is_imported: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ObjectLogEntry"]]

    def __init__(
            self,
            type: ObjectLogEntryType,
            object_id: int,
            user_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            is_imported: bool = False
    ) -> None:
        super().__init__(
            type=type,
            object_id=object_id,
            user_id=user_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            is_imported=is_imported
        )
        self.user: typing.Optional['User'] = None

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, ObjectLogEntry) and \
            self.id == other.id and \
            self.type == other.type and \
            self.object_id == other.object_id and \
            self.user_id == other.user_id and \
            self.data == other.data and \
            self.utc_datetime == other.utc_datetime

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, object_id={self.object_id}, user_id={self.user_id}, utc_datetime={self.utc_datetime}, data={self.data})>'
