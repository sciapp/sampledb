# coding: utf-8
"""

"""
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .groups import Group
from .users import User
from .locations import Location
from .permissions import Permissions
from .utils import Model

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserLocationPermissions(Model):
    __tablename__ = 'user_location_permissions'

    location_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["UserLocationPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(location_id, user_id),
    )


class GroupLocationPermissions(Model):
    __tablename__ = 'group_location_permissions'

    location_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["GroupLocationPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(location_id, group_id),
    )


class ProjectLocationPermissions(Model):
    __tablename__ = 'project_location_permissions'

    location_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    project_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ProjectLocationPermissions"]]

    __table_args__ = (
        db.PrimaryKeyConstraint(location_id, project_id),
    )


class AllUserLocationPermissions(Model):
    __tablename__ = 'all_user_location_permissions'

    location_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Location.id), primary_key=True)
    permissions: Mapped[Permissions] = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["AllUserLocationPermissions"]]
