# coding: utf-8
"""

"""

import enum
import sqlalchemy.dialects.postgresql as postgresql
from .. import db


@enum.unique
class ComponentAuthenticationType(enum.Enum):
    TOKEN = 1


class ComponentAuthentication(db.Model):
    __tablename__ = "component_authentications"

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    login = db.Column(postgresql.JSONB)
    type = db.Column(db.Enum(ComponentAuthenticationType))
    component = db.relationship('Component')

    def __init__(self, login, authentication_type, component_id):
        self.login = login
        self.type = authentication_type
        self.component_id = component_id

    def __repr__(self):
        return '<{0}(id={1.id})>'.format(type(self).__name__, self)


class OwnComponentAuthentication(db.Model):
    __tablename__ = "own_component_authentications"

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    login = db.Column(postgresql.JSONB)
    type = db.Column(db.Enum(ComponentAuthenticationType))
    component = db.relationship('Component')

    def __init__(self, login, authentication_type, component_id):
        self.login = login
        self.type = authentication_type
        self.component_id = component_id

    def __repr__(self):
        return '<{0}(id={1.id})>'.format(type(self).__name__, self)
