# coding: utf-8
"""

"""

from .. import db
from .groups import Group
from .users import User
from .actions import Action
from .permissions import Permissions
from .projects import Project

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserActionPermissions(db.Model):
    __tablename__ = 'user_action_permissions'

    action_id = db.Column(db.Integer, db.ForeignKey(Action.id), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(action_id, user_id),
        {},
    )


class GroupActionPermissions(db.Model):
    __tablename__ = 'group_action_permissions'

    action_id = db.Column(db.Integer, db.ForeignKey(Action.id), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(action_id, group_id),
        {},
    )


class ProjectActionPermissions(db.Model):
    __tablename__ = 'project_action_permissions'

    action_id = db.Column(db.Integer, db.ForeignKey(Action.id), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id, ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(action_id, project_id),
        {},
    )


class PublicActions(db.Model):
    __tablename__ = 'public_actions'

    action_id = db.Column(db.Integer, db.ForeignKey(Action.id), primary_key=True)
