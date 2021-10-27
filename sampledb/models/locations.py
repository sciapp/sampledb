# coding: utf-8
"""

"""

import datetime
import typing

from .. import db

from .objects import Objects
from .users import User
import sqlalchemy.dialects.postgresql as postgresql


class Location(db.Model):
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

    def __init__(self, name: typing.Optional[typing.Dict[str, str]], description: typing.Optional[typing.Dict[str, str]], parent_location_id: typing.Optional[int] = None, fed_id: typing.Optional[int] = None, component_id: typing.Optional[int] = None):
        self.name = name
        self.description = description
        self.parent_location_id = parent_location_id
        self.fed_id = fed_id
        self.component_id = component_id

    def __repr__(self):
        return '<{0}(id={1.id}, name="{1.name}", description="{1.description}", parent_location_id={1.parent_location_id})>'.format(type(self).__name__, self)


class ObjectLocationAssignment(db.Model):
    __tablename__ = 'object_location_assignments'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (description IS NOT NULL AND user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
            name='object_location_assignments_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='object_location_assignments_fed_id_component_id_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    description = db.Column(postgresql.JSON, nullable=True)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    location = db.relationship('Location')
    fed_id = db.Column(db.Integer, nullable=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component = db.relationship('Component')

    def __init__(self, object_id: int, location_id: int, user_id: int, description: dict, utc_datetime: typing.Optional[datetime.datetime] = None, responsible_user_id: typing.Optional[int] = None, confirmed: bool = False, fed_id: int = None, component_id: int = None):
        self.object_id = object_id
        self.location_id = location_id
        self.user_id = user_id
        self.description = description
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.responsible_user_id = responsible_user_id
        self.confirmed = confirmed
        self.fed_id = fed_id
        self.component_id = component_id

    def __repr__(self):
        return '<{0}(id={1.id}, object_id={1.object_id}, location_id={1.location_id}, user_id={1.user_id}, responsible_user_id={1.responsible_user_id}, utc_datetime={1.utc_datetime}, description="{1.description}", confirmed={1.confirmed})>'.format(type(self).__name__, self)
