# coding: utf-8
"""

"""

from .. import db
from .object_permissions import Permissions
from .groups import Group
from .users import User
import sqlalchemy.dialects.postgresql as postgresql


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(postgresql.JSON, nullable=False)
    description = db.Column(postgresql.JSON, nullable=False)


class UserProjectPermissions(db.Model):
    __tablename__ = 'user_project_permissions'

    project_id = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(project_id, user_id),
        {},
    )


class GroupProjectPermissions(db.Model):
    __tablename__ = 'group_project_permissions'

    project_id = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(project_id, group_id),
        {},
    )


class SubprojectRelationship(db.Model):
    __tablename__ = 'subproject_relationship'

    parent_project_id = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    child_project_id = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    child_can_add_users_to_parent = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.PrimaryKeyConstraint(parent_project_id, child_project_id),
        {},
    )


class ProjectInvitation(db.Model):
    __tablename__ = 'project_invitations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    accepted = db.Column(db.Boolean, nullable=False, default=False)


class ProjectObjectAssociation(db.Model):
    __tablename__ = 'project_object_association'

    project_id = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey('objects_current.object_id', ondelete="CASCADE"), nullable=False, unique=True)
