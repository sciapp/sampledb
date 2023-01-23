# coding: utf-8
"""

"""

import enum
import typing

import sqlalchemy.dialects.postgresql as postgresql
from .. import db


@enum.unique
class AuthenticationType(enum.Enum):
    LDAP = 1
    EMAIL = 2
    OTHER = 3
    API_TOKEN = 4


class Authentication(db.Model):  # type: ignore
    __tablename__ = "authentications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    login = db.Column(postgresql.JSONB)
    type = db.Column(db.Enum(AuthenticationType))
    confirmed = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User', backref="authentication_methods")

    def __init__(
            self,
            login: typing.Dict[str, typing.Any],
            authentication_type: AuthenticationType,
            confirmed: bool,
            user_id: int
    ) -> None:
        self.login = login
        self.type = authentication_type
        self.confirmed = confirmed
        self.user_id = user_id

    def __repr__(self) -> str:
        return '<{0}(id={1.id})>'.format(type(self).__name__, self)


class TwoFactorAuthenticationMethod(db.Model):  # type: ignore
    __tablename__ = "two_factor_authentication_methods"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    active = db.Column(db.Boolean, default=False, nullable=False)
    data = db.Column(postgresql.JSONB)
