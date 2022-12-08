# coding: utf-8
"""

"""

import datetime
import typing

from .. import db

from .objects import Objects
from .users import User
import sqlalchemy.dialects.postgresql as postgresql


location_user_association_table = db.Table(
    'location_responsible_users',
    db.metadata,
    db.Column('location_id', db.Integer, db.ForeignKey('locations.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)


class LocationType(db.Model):  # type: ignore
    __tablename__ = 'location_types'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (name is NOT NULL)',
            name='location_types_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='location_types_fed_id_component_id_key'),
    )

    # default location type IDs
    # offset to -100 to allow later addition of new default location types
    # see: migrations/location_types_create_default_location_types.py
    LOCATION = -100 + 1

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(postgresql.JSON, nullable=True)
    location_name_singular = db.Column(postgresql.JSON, nullable=True)
    location_name_plural = db.Column(postgresql.JSON, nullable=True)
    admin_only = db.Column(db.Boolean, nullable=False)
    enable_parent_location = db.Column(db.Boolean, nullable=False)
    enable_sub_locations = db.Column(db.Boolean, nullable=False)
    enable_object_assignments = db.Column(db.Boolean, nullable=False)
    enable_responsible_users = db.Column(db.Boolean, nullable=False)
    enable_instruments = db.Column(db.Boolean, nullable=False)
    show_location_log = db.Column(db.Boolean, nullable=False)
    fed_id = db.Column(db.Integer, nullable=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component = db.relationship('Component')

    def __init__(
            self,
            name: typing.Optional[typing.Dict[str, str]],
            location_name_singular: typing.Optional[typing.Dict[str, str]],
            location_name_plural: typing.Optional[typing.Dict[str, str]],
            admin_only: bool,
            enable_parent_location: bool,
            enable_sub_locations: bool,
            enable_object_assignments: bool,
            enable_responsible_users: bool,
            enable_instruments: bool,
            show_location_log: bool,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None
    ) -> None:
        self.name = name
        self.location_name_singular = location_name_singular
        self.location_name_plural = location_name_plural
        self.admin_only = admin_only
        self.enable_parent_location = enable_parent_location
        self.enable_sub_locations = enable_sub_locations
        self.enable_object_assignments = enable_object_assignments
        self.enable_responsible_users = enable_responsible_users
        self.enable_instruments = enable_instruments
        self.show_location_log = show_location_log
        self.fed_id = fed_id
        self.component_id = component_id

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, name="{1.name}")>'.format(type(self).__name__, self)


class Location(db.Model):  # type: ignore
    __tablename__ = 'locations'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (name is NOT NULL AND description IS NOT NULL)',
            name='locations_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='locations_fed_id_component_id_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(postgresql.JSON, nullable=True)
    description = db.Column(postgresql.JSON, nullable=True)
    parent_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    fed_id = db.Column(db.Integer, nullable=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component = db.relationship('Component')
    type_id = db.Column(db.Integer, db.ForeignKey('location_types.id'), nullable=False)
    type = db.relationship('LocationType')
    responsible_users = db.relationship("User", secondary=location_user_association_table, order_by="User.name")
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(
            self,
            name: typing.Optional[typing.Dict[str, str]],
            description: typing.Optional[typing.Dict[str, str]],
            parent_location_id: typing.Optional[int] = None,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None,
            type_id: typing.Optional[int] = None
    ) -> None:
        self.name = name
        self.description = description
        self.parent_location_id = parent_location_id
        self.fed_id = fed_id
        self.component_id = component_id
        self.type_id = type_id

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, name="{1.name}", description="{1.description}", parent_location_id={1.parent_location_id})>'.format(type(self).__name__, self)


class ObjectLocationAssignment(db.Model):  # type: ignore
    __tablename__ = 'object_location_assignments'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (description IS NOT NULL AND user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
            name='object_location_assignments_not_null_check'
        ),
        db.CheckConstraint(
            'NOT (confirmed AND declined)',
            name='object_location_assignments_not_both_states_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='object_location_assignments_fed_id_component_id_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    description = db.Column(postgresql.JSON, nullable=True)
    utc_datetime = db.Column(db.DateTime, nullable=True)
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    location = db.relationship('Location')
    fed_id = db.Column(db.Integer, nullable=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component = db.relationship('Component')
    declined = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(
            self,
            object_id: int,
            location_id: typing.Optional[int],
            user_id: typing.Optional[int],
            description: typing.Optional[typing.Dict[str, str]],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            responsible_user_id: typing.Optional[int] = None,
            confirmed: bool = False,
            declined: bool = False,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None
    ) -> None:
        self.object_id = object_id
        self.location_id = location_id
        self.user_id = user_id
        self.description = description
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.responsible_user_id = responsible_user_id
        self.confirmed = confirmed
        self.declined = declined
        self.fed_id = fed_id
        self.component_id = component_id

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, object_id={1.object_id}, location_id={1.location_id}, user_id={1.user_id}, responsible_user_id={1.responsible_user_id}, utc_datetime={1.utc_datetime}, description="{1.description}", confirmed={1.confirmed}, declined={1.declined})>'.format(type(self).__name__, self)
