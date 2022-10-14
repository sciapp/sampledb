# coding: utf-8
"""

"""

from .. import db
from .groups import Group
from .users import User
from .locations import Location
from .permissions import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserLocationPermissions(db.Model):  # type: ignore
    __tablename__ = 'user_location_permissions'

    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(location_id, user_id),
    )


class GroupLocationPermissions(db.Model):  # type: ignore
    __tablename__ = 'group_location_permissions'

    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(location_id, group_id),
    )


class ProjectLocationPermissions(db.Model):  # type: ignore
    __tablename__ = 'project_location_permissions'

    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(location_id, project_id),
    )


class AllUserLocationPermissions(db.Model):  # type: ignore
    __tablename__ = 'all_user_location_permissions'

    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), primary_key=True)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)
