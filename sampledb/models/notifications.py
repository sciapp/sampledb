# coding: utf-8
"""

"""

import enum
import datetime
import typing

from .. import db

from .users import User


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


@enum.unique
class NotificationMode(enum.Enum):
    IGNORE = 0
    WEBAPP = 1
    EMAIL = 2


class Notification(db.Model):  # type: ignore
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(NotificationType), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    was_read = db.Column(db.Boolean, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)

    def __init__(
            self,
            type: NotificationType,
            user_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        self.type = type
        self.user_id = user_id
        self.data = data
        self.was_read = False
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, data={self.data})>'


class NotificationModeForType(db.Model):  # type: ignore
    __tablename__ = 'notification_mode_for_types'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(NotificationType), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    mode = db.Column(db.Enum(NotificationMode), nullable=False)
    __table_args__ = (
        db.UniqueConstraint('type', 'user_id', name='_notification_mode_for_types_uc'),
    )

    def __init__(
            self,
            type: typing.Optional[NotificationType],
            user_id: int,
            mode: NotificationMode
    ) -> None:
        self.type = type
        self.user_id = user_id
        self.mode = mode

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(type={self.type}, user_id={self.user_id}, mode={self.mode})>'
