# coding: utf-8
"""

"""

from .. import db
from .groups import Group
from .users import User
from .permissions import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


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
