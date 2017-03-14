# coding: utf-8
"""

"""

import enum
import flask_login
from .. import db


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

    def __init__(self, name, email, type):
        self.name = name
        self.email = email
        self.type = type

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.name})>'.format(type(self).__name__, self)
