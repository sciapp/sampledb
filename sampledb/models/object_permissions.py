# coding: utf-8
"""

"""

from .. import db
from .groups import Group
from .users import User
from .objects import Objects
from .permissions import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserObjectPermissions(db.Model):  # type: ignore
    __tablename__ = 'user_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, user_id),
    )


class GroupObjectPermissions(db.Model):  # type: ignore
    __tablename__ = 'group_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, group_id),
    )


class ProjectObjectPermissions(db.Model):  # type: ignore
    __tablename__ = 'project_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, project_id),
    )


class AllUserObjectPermissions(db.Model):  # type: ignore
    __tablename__ = 'all_user_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)


class AnonymousUserObjectPermissions(db.Model):  # type: ignore
    __tablename__ = 'anonymous_user_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)
