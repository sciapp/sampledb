# coding: utf-8
"""

"""
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .groups import Group
from .users import User
from .permissions import Permissions
from .utils import Model


class DefaultUserPermissions(Model):
    __tablename__ = 'default_user_permissions'

    creator_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["DefaultUserPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(creator_id, user_id),
    )


class DefaultGroupPermissions(Model):
    __tablename__ = 'default_group_permissions'

    creator_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["DefaultGroupPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(creator_id, group_id),
    )


class DefaultProjectPermissions(Model):
    __tablename__ = 'default_project_permissions'

    creator_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["DefaultProjectPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(creator_id, project_id),
    )


class AllUserDefaultPermissions(Model):
    __tablename__ = 'all_user_default_permissions'

    creator_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["AllUserDefaultPermissions"]]
