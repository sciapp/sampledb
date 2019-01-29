# coding: utf-8
"""

"""

from .. import db
from .groups import Group
from .users import User
from .objects import Objects
from .permissions import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserObjectPermissions(db.Model):
    __tablename__ = 'user_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, user_id),
        {},
    )


class GroupObjectPermissions(db.Model):
    __tablename__ = 'group_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, group_id),
        {},
    )


class ProjectObjectPermissions(db.Model):
    __tablename__ = 'project_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, project_id),
        {},
    )


class PublicObjects(db.Model):
    __tablename__ = 'public_objects'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)


class DefaultUserPermissions(db.Model):
    __tablename__ = 'default_user_permissions'

    creator_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(creator_id, user_id),
        {},
    )


class DefaultGroupPermissions(db.Model):
    __tablename__ = 'default_group_permissions'

    creator_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(creator_id, group_id),
        {},
    )


class DefaultProjectPermissions(db.Model):
    __tablename__ = 'default_project_permissions'

    creator_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(creator_id, project_id),
        {},
    )


class DefaultPublicPermissions(db.Model):
    __tablename__ = 'default_public_permissions'

    creator_id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
