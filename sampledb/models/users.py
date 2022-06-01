# coding: utf-8
"""

"""

import enum
import typing

from .. import db


@enum.unique
class UserType(enum.Enum):
    PERSON = 1
    OTHER = 2
    FEDERATION_USER = 3


class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.CheckConstraint(
            '(type = \'FEDERATION_USER\' AND NOT is_admin AND fed_id IS NOT NULL AND component_id IS NOT NULL) OR (name IS NOT NULL AND email IS NOT NULL)',
            name='users_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='users_fed_id_component_id_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=True)
    email = db.Column(db.String, nullable=True)
    type = db.Column(db.Enum(UserType), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_readonly = db.Column(db.Boolean, default=False, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    orcid = db.Column(db.String, nullable=True)
    affiliation = db.Column(db.String, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role = db.Column(db.String, nullable=True)
    extra_fields = db.Column(db.JSON, nullable=False, default={}, server_default=db.text("'{}'::json"))
    fed_id = db.Column(db.Integer, nullable=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component = db.relationship('Component')

    def __init__(self, name, email, type, orcid: typing.Optional[str] = None, affiliation: typing.Optional[str] = None, role: typing.Optional[str] = None, extra_fields: typing.Optional[dict] = {}, fed_id: typing.Optional[int] = None, component_id: typing.Optional[int] = None):
        self.name = name
        self.email = email
        self.type = type
        self.orcid = orcid
        self.affiliation = affiliation
        self.role = role
        self.extra_fields = extra_fields
        self.fed_id = fed_id
        self.component_id = component_id

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
                self.orcid == other.orcid and
                self.fed_id == other.fed_id and
                self.component_id == other.component_id
            )
        except AttributeError:
            return False

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.name})>'.format(type(self).__name__, self)


class UserInvitation(db.Model):
    __tablename__ = 'user_invitations'

    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    accepted = db.Column(db.Boolean, nullable=False, default=False)


class UserFederationAlias(db.Model):
    __tablename__ = 'fed_user_aliases'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    name = db.Column(db.String, nullable=True)
    email = db.Column(db.String, nullable=True)
    orcid = db.Column(db.String, nullable=True)
    affiliation = db.Column(db.String, nullable=True)
    role = db.Column(db.String, nullable=True)
    extra_fields = db.Column(db.JSON, nullable=False, default={}, server_default=db.text("'{}'::json"))
    user = db.relationship('User')
    component = db.relationship('Component')

    __table_args__ = (
        db.PrimaryKeyConstraint(user_id, component_id),
        {},
    )

    def __init__(self, user_id: int, component_id: int, name: typing.Optional[str] = None, email: typing.Optional[str] = None, orcid: typing.Optional[str] = None, affiliation: typing.Optional[str] = None, role: typing.Optional[str] = None, extra_fields: typing.Optional[dict] = {}):
        self.user_id = user_id
        self.component_id = component_id
        self.name = name
        self.email = email
        self.orcid = orcid
        self.affiliation = affiliation
        self.role = role
        self.extra_fields = extra_fields

    def __repr__(self):
        return '<{0}(user_id={1.user_id}, component_id={1.component_id}; name={1.name})>'.format(type(self).__name__, self)
