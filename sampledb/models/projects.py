# coding: utf-8
"""

"""
import datetime
import typing

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, Query, relationship

from .. import db
from .permissions import Permissions
from .groups import Group
from .users import User
from .utils import Model

if typing.TYPE_CHECKING:
    from .group_categories import GroupCategory


class Project(Model):
    __tablename__ = 'projects'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSON, nullable=False)
    description: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSON, nullable=False)
    categories: Mapped[typing.List['GroupCategory']] = relationship('GroupCategory', secondary='project_group_category_association_table', back_populates='project_groups')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Project"]]


class UserProjectPermissions(Model):
    __tablename__ = 'user_project_permissions'

    project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["UserProjectPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(project_id, user_id),
    )


class GroupProjectPermissions(Model):
    __tablename__ = 'group_project_permissions'

    project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["GroupProjectPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(project_id, group_id),
    )


class SubprojectRelationship(Model):
    __tablename__ = 'subproject_relationship'

    parent_project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    child_project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    child_can_add_users_to_parent: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["SubprojectRelationship"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(parent_project_id, child_project_id),
    )


class ProjectInvitation(Model):
    __tablename__ = 'project_invitations'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    inviter_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    accepted: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    revoked: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())  # TODO: migration

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ProjectInvitation"]]


class ProjectObjectAssociation(Model):
    __tablename__ = 'project_object_association'

    project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), primary_key=True)
    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('objects_current.object_id', ondelete="CASCADE"), nullable=False, unique=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ProjectObjectAssociation"]]
