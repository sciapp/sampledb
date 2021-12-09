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

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(postgresql.JSON, nullable=False)
    description = db.Column(postgresql.JSON, nullable=False)
    parent_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)

    def __init__(self, name: dict, description: dict, parent_location_id: typing.Optional[int] = None):
        self.name = name
        self.description = description
        self.parent_location_id = parent_location_id

    def __repr__(self):
        return '<{0}(id={1.id}, name="{1.name}", description="{1.description}", parent_location_id={1.parent_location_id})>'.format(type(self).__name__, self)


class ObjectLocationAssignment(db.Model):
    __tablename__ = 'object_location_assignments'

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    description = db.Column(postgresql.JSON, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    location = db.relationship('Location')

    def __init__(self, object_id: int, location_id: int, user_id: int, description: dict, utc_datetime: typing.Optional[datetime.datetime] = None, responsible_user_id: typing.Optional[int] = None, confirmed: bool = False):
        self.object_id = object_id
        self.location_id = location_id
        self.user_id = user_id
        self.description = description
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.responsible_user_id = responsible_user_id
        self.confirmed = confirmed

    def __repr__(self):
        return '<{0}(id={1.id}, object_id={1.object_id}, location_id={1.location_id}, user_id={1.user_id}, responsible_user_id={1.responsible_user_id}, utc_datetime={1.utc_datetime}, description="{1.description}", confirmed={1.confirmed})>'.format(type(self).__name__, self)
