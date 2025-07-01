# coding: utf-8
"""
Models for imported .eln files.
"""
import datetime
import typing

from sqlalchemy.orm import Mapped, Query, relationship

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User


class ELNImport(Model):
    __tablename__ = 'eln_imports'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    file_name: Mapped[str] = db.Column(db.String, nullable=False)
    binary_data: Mapped[bytes] = db.deferred(db.Column(db.LargeBinary, nullable=False))
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id', use_alter=True, ondelete='CASCADE', name="fk_eln_imports_user_id"), nullable=False)
    upload_utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    import_utc_datetime: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    invalid_reason: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    user: Mapped['User'] = relationship('User', foreign_keys=[user_id])
    signed_by: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    objects: Mapped[typing.List['ELNImportObject']] = relationship('ELNImportObject', back_populates='eln_import')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ELNImport"]]


class ELNImportAction(Model):
    __tablename__ = 'eln_import_actions'

    action_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('actions.id'), primary_key=True)
    action_type_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('action_types.id'), nullable=True, unique=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ELNImportAction"]]


class ELNImportObject(Model):
    __tablename__ = 'eln_import_objects'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('objects_current.object_id'), primary_key=True)
    eln_import_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('eln_imports.id'), nullable=False)
    url: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    eln_import: Mapped[ELNImport] = relationship('ELNImport', back_populates='objects')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ELNImportObject"]]
