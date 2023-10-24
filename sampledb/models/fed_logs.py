# coding: utf-8
"""

"""

import enum
import datetime
import typing

from sqlalchemy.orm import Mapped, Query, relationship

from .files import File
from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User


@enum.unique
class FedUserLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_USER = 1
    UPDATE_USER = 2
    SHARE_USER = 3
    UPDATE_SHARED_USER = 4
    UPDATE_USER_POLICY = 5
    CREATE_REF_USER = 6


class FedUserLogEntry(Model):
    __tablename__ = 'fed_user_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedUserLogEntryType] = db.Column(db.Enum(FedUserLogEntryType), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedUserLogEntry"]]

    def __init__(
            self,
            type: FedUserLogEntryType,
            user_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            user_id=user_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, user_id={self.user_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedObjectLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_OBJECT = 1
    UPDATE_OBJECT = 2
    ADD_POLICY = 3
    UPDATE_SHARED_OBJECT = 4
    UPDATE_OBJECT_POLICY = 5
    CREATE_REF_OBJECT = 6
    REMOTE_IMPORT_OBJECT = 7


class FedObjectLogEntry(Model):
    __tablename__ = 'fed_object_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedObjectLogEntryType] = db.Column(db.Enum(FedObjectLogEntryType), nullable=False)
    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('objects_current.object_id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    user_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user: Mapped[typing.Optional['User']] = relationship('User')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedObjectLogEntry"]]

    def __init__(
            self,
            type: FedObjectLogEntryType,
            object_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            user_id: typing.Optional[int] = None
    ) -> None:
        super().__init__(
            type=type,
            object_id=object_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            user_id=user_id
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, object_id={self.object_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedLocationLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_LOCATION = 1
    UPDATE_LOCATION = 2
    SHARE_LOCATION = 3
    UPDATE_SHARED_LOCATION = 4
    UPDATE_LOCATION_POLICY = 5
    CREATE_REF_LOCATION = 6


class FedLocationLogEntry(Model):
    __tablename__ = 'fed_location_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedLocationLogEntryType] = db.Column(db.Enum(FedLocationLogEntryType), nullable=False)
    location_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedLocationLogEntry"]]

    def __init__(
            self,
            type: FedLocationLogEntryType,
            location_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            location_id=location_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, location_id={self.location_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedLocationTypeLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_LOCATION_TYPE = 1
    UPDATE_LOCATION_TYPE = 2
    SHARE_LOCATION_TYPE = 3
    UPDATE_SHARED_LOCATION_TYPE = 4
    UPDATE_LOCATION_TYPE_POLICY = 5
    CREATE_REF_LOCATION_TYPE = 6


class FedLocationTypeLogEntry(Model):
    __tablename__ = 'fed_location_type_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedLocationTypeLogEntryType] = db.Column(db.Enum(FedLocationTypeLogEntryType), nullable=False)
    location_type_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('location_types.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedLocationTypeLogEntry"]]

    def __init__(
            self,
            type: FedLocationTypeLogEntryType,
            location_type_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            location_type_id=location_type_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, location_type_id={self.location_type_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedActionLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_ACTION = 1
    UPDATE_ACTION = 2
    SHARE_ACTION = 3
    UPDATE_SHARED_ACTION = 4
    UPDATE_ACTION_POLICY = 5
    CREATE_REF_ACTION = 6


class FedActionLogEntry(Model):
    __tablename__ = 'fed_action_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedActionLogEntryType] = db.Column(db.Enum(FedActionLogEntryType), nullable=False)
    action_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedActionLogEntry"]]

    def __init__(
            self,
            type: FedActionLogEntryType,
            action_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            action_id=action_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, action_id={self.action_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedActionTypeLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_ACTION_TYPE = 1
    UPDATE_ACTION_TYPE = 2
    SHARE_ACTION_TYPE = 3
    UPDATE_SHARED_ACTION_TYPE = 4
    UPDATE_ACTION_TYPE_POLICY = 5
    CREATE_REF_ACTION_TYPE = 6


class FedActionTypeLogEntry(Model):
    __tablename__ = 'fed_action_type_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedActionTypeLogEntryType] = db.Column(db.Enum(FedActionTypeLogEntryType), nullable=False)
    action_type_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('action_types.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedActionTypeLogEntry"]]

    def __init__(
            self,
            type: FedActionTypeLogEntryType,
            action_type_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            action_type_id=action_type_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, action_type_id={self.action_type_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedInstrumentLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_INSTRUMENT = 1
    UPDATE_INSTRUMENT = 2
    SHARE_INSTRUMENT = 3
    UPDATE_SHARED_INSTRUMENT = 4
    UPDATE_INSTRUMENT_POLICY = 5
    CREATE_REF_INSTRUMENT = 6


class FedInstrumentLogEntry(Model):
    __tablename__ = 'fed_instrument_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedInstrumentLogEntryType] = db.Column(db.Enum(FedInstrumentLogEntryType), nullable=False)
    instrument_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedInstrumentLogEntry"]]

    def __init__(
            self,
            type: FedInstrumentLogEntryType,
            instrument_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            instrument_id=instrument_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, instrument_id={self.instrument_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedCommentLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_COMMENT = 1
    UPDATE_COMMENT = 2
    SHARE_COMMENT = 3
    UPDATE_SHARED_COMMENT = 4
    UPDATE_COMMENT_POLICY = 5
    CREATE_REF_COMMENT = 6


class FedCommentLogEntry(Model):
    __tablename__ = 'fed_comment_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedCommentLogEntryType] = db.Column(db.Enum(FedCommentLogEntryType), nullable=False)
    comment_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedCommentLogEntry"]]

    def __init__(
            self,
            type: FedCommentLogEntryType,
            comment_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            comment_id=comment_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, comment_id={self.comment_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedFileLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_FILE = 1
    UPDATE_FILE = 2
    SHARE_FILE = 3
    UPDATE_SHARED_FILE = 4
    UPDATE_FILE_POLICY = 5
    CREATE_REF_FILE = 6


class FedFileLogEntry(Model):
    __tablename__ = 'fed_file_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedFileLogEntryType] = db.Column(db.Enum(FedFileLogEntryType), nullable=False)
    object_id: Mapped[int] = db.Column(db.Integer, nullable=False)
    file_id: Mapped[int] = db.Column(db.Integer, nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedFileLogEntry"]]

    __table_args__ = (
        db.ForeignKeyConstraint([object_id, file_id], [File.object_id, File.id]),
    )

    def __init__(
            self,
            type: FedFileLogEntryType,
            object_id: int,
            file_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            object_id=object_id,
            file_id=file_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, file_id={self.file_id}, utc_datetime={self.utc_datetime}, data={self.data})>'


@enum.unique
class FedObjectLocationAssignmentLogEntryType(enum.Enum):
    OTHER = 0
    IMPORT_OBJECT_LOCATION_ASSIGNMENT = 1
    UPDATE_OBJECT_LOCATION_ASSIGNMENT = 2
    SHARE_OBJECT_LOCATION_ASSIGNMENT = 3
    UPDATE_SHARED_OBJECT_LOCATION_ASSIGNMENT = 4
    UPDATE_OBJECT_LOCATION_ASSIGNMENT_POLICY = 5
    CREATE_REF_OBJECT_LOCATION_ASSIGNMENT = 6


class FedObjectLocationAssignmentLogEntry(Model):
    __tablename__ = 'fed_object_location_assignment_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[FedObjectLocationAssignmentLogEntryType] = db.Column(db.Enum(FedObjectLocationAssignmentLogEntryType), nullable=False)
    object_location_assignment_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('object_location_assignments.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FedObjectLocationAssignmentLogEntry"]]

    def __init__(
            self,
            type: FedObjectLocationAssignmentLogEntryType,
            object_location_assignment_id: int,
            component_id: int,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            object_location_assignment_id=object_location_assignment_id,
            component_id=component_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, object_location_assignment_id={self.object_location_assignment_id}, utc_datetime={self.utc_datetime}, data={self.data})>'
