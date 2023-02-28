# coding: utf-8
"""

"""
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .groups import Group
from .users import User
from .actions import Action
from .permissions import Permissions
from .projects import Project
from .utils import Model

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserActionPermissions(Model):
    __tablename__ = 'user_action_permissions'

    action_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Action.id), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["UserActionPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(action_id, user_id),
    )


class GroupActionPermissions(Model):
    __tablename__ = 'group_action_permissions'

    action_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Action.id), nullable=False)
    group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["GroupActionPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(action_id, group_id),
    )


class ProjectActionPermissions(Model):
    __tablename__ = 'project_action_permissions'

    action_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Action.id), nullable=False)
    project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ProjectActionPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(action_id, project_id),
    )


class AllUserActionPermissions(Model):
    __tablename__ = 'all_user_action_permissions'

    action_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Action.id), primary_key=True)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["AllUserActionPermissions"]]
