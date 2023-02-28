# coding: utf-8
"""

"""
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .groups import Group
from .users import User
from .objects import Objects
from .permissions import Permissions
from .utils import Model

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserObjectPermissions(Model):
    __tablename__ = 'user_object_permissions'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["UserObjectPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, user_id),
    )


class GroupObjectPermissions(Model):
    __tablename__ = 'group_object_permissions'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["GroupObjectPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, group_id),
    )


class ProjectObjectPermissions(Model):
    __tablename__ = 'project_object_permissions'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ProjectObjectPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, project_id),
    )


class AllUserObjectPermissions(Model):
    __tablename__ = 'all_user_object_permissions'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["AllUserObjectPermissions"]]


class AnonymousUserObjectPermissions(Model):
    __tablename__ = 'anonymous_user_object_permissions'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["AnonymousUserObjectPermissions"]]
