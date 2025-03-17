# coding: utf-8
"""

"""

import enum
import datetime
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .users import User
from .utils import Model


@enum.unique
class NotificationType(enum.Enum):
    OTHER = 0
    ASSIGNED_AS_RESPONSIBLE_USER = 1
    INVITED_TO_GROUP = 2
    INVITED_TO_PROJECT = 3
    ANNOUNCEMENT = 4
    RECEIVED_OBJECT_PERMISSIONS_REQUEST = 5
    INSTRUMENT_LOG_ENTRY_CREATED = 6
    REFERENCED_BY_OBJECT_METADATA = 7
    INSTRUMENT_LOG_ENTRY_EDITED = 8
    RESPONSIBILITY_ASSIGNMENT_DECLINED = 9
    REMOTE_OBJECT_IMPORT_FAILED = 10
    REMOTE_OBJECT_IMPORT_NOTES = 11
    AUTOMATIC_USER_FEDERATION = 12
    # Document any additional values in docs/administrator_guide/configuration.rst


@enum.unique
class NotificationMode(enum.Enum):
    IGNORE = 0
    WEBAPP = 1
    EMAIL = 2


class Notification(Model):
    __tablename__ = 'notifications'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[NotificationType] = db.Column(db.Enum(NotificationType), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    was_read: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Notification"]]

    def __init__(
            self,
            type: NotificationType,
            user_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            user_id=user_id,
            data=data,
            was_read=False,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, data={self.data})>'


class NotificationModeForType(Model):
    __tablename__ = 'notification_mode_for_types'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[NotificationType] = db.Column(db.Enum(NotificationType), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    mode: Mapped[NotificationMode] = db.Column(db.Enum(NotificationMode), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["NotificationModeForType"]]

    __table_args__ = (
        db.UniqueConstraint('type', 'user_id', name='_notification_mode_for_types_uc'),
    )

    def __init__(
            self,
            type: NotificationType,
            user_id: int,
            mode: NotificationMode
    ) -> None:
        super().__init__(
            type=type,
            user_id=user_id,
            mode=mode
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(type={self.type}, user_id={self.user_id}, mode={self.mode})>'
