# coding: utf-8
"""

"""

import enum
import flask_login
import sqlalchemy.dialects.postgresql as postgresql
from sampledb import db


@enum.unique
class AuthenticationType(enum.Enum):
    LDAP = 1
    EMAIL = 2
    OTHER = 3


class Authentication(db.Model):
    __tablename__ = "authentications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    login = db.Column(postgresql.JSONB)
    type = db.Column(db.Enum(AuthenticationType))
    user = db.relationship('User', backref="authentication_methods")

    def __init__(self, login, authentication_type, user_id):
        self.login = login
        self.type = authentication_type
        self.user_id = user_id

    def __repr__(self):
        return '<{0}(id={1.id})>'.format(type(self).__name__, self)


@enum.unique
class UserType(enum.Enum):
    PERSON = 1
    OTHER = 2


class User(db.Model, flask_login.UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    type = db.Column(db.Enum(UserType), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, name, email, user_type):
        self.name = name
        self.email = email
        self.type = user_type

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.name})>'.format(type(self).__name__, self)
