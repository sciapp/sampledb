# coding: utf-8
"""

"""

from .. import db
from .permissions import Permissions
from .groups import Group
from .users import User


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String, nullable=False, default='')


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