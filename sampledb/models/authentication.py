# coding: utf-8
"""

"""

import enum
import sqlalchemy.dialects.postgresql as postgresql
from .. import db


@enum.unique
class AuthenticationType(enum.Enum):
    LDAP = 1
    EMAIL = 2
    OTHER = 3
    API_TOKEN = 4


class Authentication(db.Model):
    __tablename__ = "authentications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    login = db.Column(postgresql.JSONB)
    type = db.Column(db.Enum(AuthenticationType))
    confirmed = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User', backref="authentication_methods")

    def __init__(self, login, authentication_type, confirmed, user_id):
        self.login = login
        self.type = authentication_type
        self.confirmed = confirmed
        self.user_id = user_id

    def __repr__(self):
        return '<{0}(id={1.id})>'.format(type(self).__name__, self)


class TwoFactorAuthenticationMethod(db.Model):
    __tablename__ = "two_factor_authentication_methods"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    active = db.Column(db.Boolean, default=False, nullable=False)
    data = db.Column(postgresql.JSONB)
