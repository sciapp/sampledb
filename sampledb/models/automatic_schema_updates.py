import enum
import datetime
import typing

from sqlalchemy.orm import Mapped, Query, relationship
from sqlalchemy.dialects import postgresql

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User


@enum.unique
class UpdatableObjectsCheckStatus(enum.Enum):
    POSTED = 0
    IN_PROGRESS = 1
    DONE = 2


class UpdatableObjectsCheck(Model):
    __tablename__ = 'updatable_objects_checks'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    status: Mapped[UpdatableObjectsCheckStatus] = db.Column(db.Enum(UpdatableObjectsCheckStatus), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user: Mapped['User'] = relationship('User')
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    action_ids: Mapped[typing.Optional[typing.List[int]]] = db.Column(postgresql.JSONB, nullable=True)
    result: Mapped[typing.Dict[str, typing.Any]] = db.Column(postgresql.JSONB, nullable=True)
    automatic_schema_update: Mapped['AutomaticSchemaUpdate'] = relationship('AutomaticSchemaUpdate', back_populates='updatable_objects_check')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query['UpdatableObjectsCheck']]


@enum.unique
class AutomaticSchemaUpdateStatus(enum.Enum):
    POSTED = 0
    IN_PROGRESS = 1
    DONE = 2


class AutomaticSchemaUpdate(Model):
    __tablename__ = 'automatic_schema_updates'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    status: Mapped[AutomaticSchemaUpdateStatus] = db.Column(db.Enum(AutomaticSchemaUpdateStatus), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user: Mapped['User'] = relationship('User')
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    updatable_objects_check_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('updatable_objects_checks.id'), nullable=False, unique=True)
    updatable_objects_check: Mapped[UpdatableObjectsCheck] = relationship('UpdatableObjectsCheck', back_populates='automatic_schema_update')
    object_ids: Mapped[typing.List[int]] = db.Column(postgresql.JSONB, nullable=False)
    result: Mapped[typing.Dict[str, typing.Any]] = db.Column(postgresql.JSONB, nullable=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query['AutomaticSchemaUpdate']]
