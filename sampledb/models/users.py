# coding: utf-8
"""

"""

import enum
import typing
from datetime import datetime

from .. import db


@enum.unique
class UserType(enum.Enum):
    PERSON = 1
    OTHER = 2
    FEDERATION_USER = 3


class User(db.Model):  # type: ignore
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
    last_modified = db.Column(db.DateTime, nullable=False)
    component = db.relationship('Component')
    last_modified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def __init__(
            self,
            name: typing.Optional[str],
            email: typing.Optional[str],
            type: UserType,
            orcid: typing.Optional[str] = None,
            affiliation: typing.Optional[str] = None,
            role: typing.Optional[str] = None,
            extra_fields: typing.Optional[typing.Dict[str, str]] = None,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None,
            last_modified: typing.Optional[datetime] = None
    ) -> None:
        if extra_fields is None:
            extra_fields = {}
        self.name = name
        self.email = email
        self.type = type
        self.orcid = orcid
        self.affiliation = affiliation
        self.role = role
        self.extra_fields = extra_fields
        self.fed_id = fed_id
        self.component_id = component_id
        if last_modified is None:
            self.last_modified = datetime.utcnow()
        else:
            self.last_modified = last_modified

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, User):
            return bool(
                self.id == other.id and
                self.name == other.name and
                self.email == other.email and
                self.type == other.type and
                self.is_admin == other.is_admin and
                self.is_readonly == other.is_readonly and
                self.is_hidden == other.is_hidden and
                self.orcid == other.orcid and
                self.affiliation == other.affiliation and
                self.role == other.role and
                self.fed_id == other.fed_id and
                self.component_id == other.component_id
            )
        return NotImplemented

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, name={1.name})>'.format(type(self).__name__, self)


class UserInvitation(db.Model):  # type: ignore
    __tablename__ = 'user_invitations'

    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    accepted = db.Column(db.Boolean, nullable=False, default=False)


class UserFederationAlias(db.Model):  # type: ignore
    __tablename__ = 'fed_user_aliases'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    name = db.Column(db.String, nullable=True)
    use_real_name = db.Column(db.Boolean, nullable=False, default=False)
    email = db.Column(db.String, nullable=True)
    use_real_email = db.Column(db.Boolean, nullable=False, default=False)
    orcid = db.Column(db.String, nullable=True)
    use_real_orcid = db.Column(db.Boolean, nullable=False, default=False)
    affiliation = db.Column(db.String, nullable=True)
    use_real_affiliation = db.Column(db.Boolean, nullable=False, default=False)
    role = db.Column(db.String, nullable=True)
    use_real_role = db.Column(db.Boolean, nullable=False, default=False)
    extra_fields = db.Column(db.JSON, nullable=False, default={}, server_default=db.text("'{}'::json"))
    last_modified = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User')
    component = db.relationship('Component')

    __table_args__ = (
        db.PrimaryKeyConstraint(user_id, component_id),
    )

    def __init__(
            self,
            user_id: int,
            component_id: int,
            name: typing.Optional[str] = None,
            use_real_name: bool = False,
            email: typing.Optional[str] = None,
            use_real_email: bool = False,
            orcid: typing.Optional[str] = None,
            use_real_orcid: bool = False,
            affiliation: typing.Optional[str] = None,
            use_real_affiliation: bool = False,
            role: typing.Optional[str] = None,
            use_real_role: bool = False,
            extra_fields: typing.Optional[typing.Dict[str, str]] = None,
            last_modified: typing.Optional[datetime] = None):
        if extra_fields is None:
            extra_fields = {}
        self.user_id = user_id
        self.component_id = component_id
        self.name = name
        self.use_real_name = use_real_name
        self.email = email
        self.use_real_email = use_real_email
        self.orcid = orcid
        self.use_real_orcid = use_real_orcid
        self.affiliation = affiliation
        self.use_real_affiliation = use_real_affiliation
        self.role = role
        self.use_real_role = use_real_role
        self.extra_fields = extra_fields
        if last_modified is None:
            self.last_modified = datetime.utcnow()
        else:
            self.last_modified = last_modified

    def __repr__(self) -> str:
        return '<{0}(user_id={1.user_id}, component_id={1.component_id}; name={1.name})>'.format(type(self).__name__, self)
