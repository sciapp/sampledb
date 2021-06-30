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
    is_readonly = db.Column(db.Boolean, default=False, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    orcid = db.Column(db.String, nullable=True)
    affiliation = db.Column(db.String, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role = db.Column(db.String, nullable=True)
    extra_fields = db.Column(db.JSON, nullable=False, default={}, server_default=db.text("'{}'::json"))

    def __init__(self, name, email, type):
        self.name = name
        self.email = email
        self.type = type

    def __eq__(self, other):
        try:
            return (
                self.id == other.id and
                self.name == other.name and
                self.email == other.email and
                self.type == other.type and
                self.is_admin == other.is_admin and
                self.is_readonly == other.is_readonly and
                self.is_hidden == other.is_hidden and
                self.orcid == other.orcid
            )
        except AttributeError:
            return False

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.name})>'.format(type(self).__name__, self)


class UserInvitation(db.Model):
    __tablename__ = 'user_invitations'

    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    accepted = db.Column(db.Boolean, nullable=False, default=False)
