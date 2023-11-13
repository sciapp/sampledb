# coding: utf-8
"""

"""

import enum
import datetime
import typing

from sqlalchemy.orm import Mapped, Query, relationship

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@enum.unique
class UserLogEntryType(enum.Enum):
    OTHER = 0
    CREATE_OBJECT = 1
    EDIT_OBJECT = 2
    EDIT_OBJECT_PERMISSIONS = 3
    REGISTER_USER = 4
    INVITE_USER = 5
    EDIT_USER_PREFERENCES = 6
    RESTORE_OBJECT_VERSION = 7
    POST_COMMENT = 8
    UPLOAD_FILE = 9
    CREATE_BATCH = 10
    ASSIGN_LOCATION = 11
    CREATE_LOCATION = 12
    UPDATE_LOCATION = 13
    LINK_PUBLICATION = 14
    CREATE_INSTRUMENT_LOG_ENTRY = 15
    IMPORT_FROM_ELN_FILE = 16


class UserLogEntry(Model):
    __tablename__ = 'user_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[UserLogEntryType] = db.Column(db.Enum(UserLogEntryType), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    user: Mapped['User'] = relationship('User', back_populates="log_entries")

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["UserLogEntry"]]

    def __init__(
            self,
            type: UserLogEntryType,
            user_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            user_id=user_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, user_id={self.user_id}, utc_datetime={self.utc_datetime}, data={self.data})>'
