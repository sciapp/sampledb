# coding: utf-8
"""

"""

import enum
import typing
import datetime

from sqlalchemy.orm import Mapped, Query, relationship

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .authentication import Authentication
    from .components import Component
    from .groups import Group
    from .user_log import UserLogEntry


@enum.unique
class UserType(enum.Enum):
    PERSON = 1
    OTHER = 2
    FEDERATION_USER = 3
    ELN_IMPORT_USER = 4


class User(Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.CheckConstraint(
            '(type = \'FEDERATION_USER\' AND NOT is_admin AND fed_id IS NOT NULL AND component_id IS NOT NULL) OR (type = \'ELN_IMPORT_USER\' AND NOT is_admin AND eln_import_id IS NOT NULL AND eln_object_id IS NOT NULL) OR (name IS NOT NULL AND email IS NOT NULL)',
            name='users_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='users_fed_id_component_id_key'),
        db.UniqueConstraint('eln_import_id', 'eln_object_id', name='users_eln_import_id_eln_object_id_key'),
    )

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    email: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    type: Mapped[UserType] = db.Column(db.Enum(UserType), nullable=False)
    is_admin: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    is_readonly: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    is_hidden: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    orcid: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    affiliation: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    is_active: Mapped[bool] = db.Column(db.Boolean, default=True, nullable=False)
    role: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    extra_fields: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False, default={}, server_default=db.text("'{}'::json"))
    fed_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)
    component_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    last_modified: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    component: Mapped[typing.Optional['Component']] = relationship('Component')
    last_modified_by_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # named foreign key constraint to allow for manual deletion in empty_database()
    eln_import_id = db.Column(db.Integer, db.ForeignKey('eln_imports.id', use_alter=True, name='fk_users_eln_import_id'), nullable=True)
    eln_object_id = db.Column(db.String, nullable=True)
    eln_import = db.relationship('ELNImport', foreign_keys=[eln_import_id])
    groups: Mapped[typing.List['Group']] = relationship('Group', secondary='user_group_memberships', back_populates='members')
    log_entries: Mapped[typing.List['UserLogEntry']] = relationship('UserLogEntry', back_populates="user")
    authentication_methods: Mapped[typing.List['Authentication']] = relationship('Authentication', back_populates='user')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["User"]]

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
            last_modified: typing.Optional[datetime.datetime] = None,
            *,
            eln_import_id: typing.Optional[int] = None,
            eln_object_id: typing.Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            email=email,
            type=type,
            orcid=orcid,
            affiliation=affiliation,
            role=role,
            extra_fields=extra_fields if extra_fields is not None else {},
            fed_id=fed_id,
            component_id=component_id,
            last_modified=last_modified if last_modified is not None else datetime.datetime.now(datetime.timezone.utc),
            eln_import_id=eln_import_id,
            eln_object_id=eln_object_id
        )

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
                self.component_id == other.component_id and
                self.eln_import_id == other.eln_import_id and
                self.eln_object_id == other.eln_object_id
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, name={self.name})>'


class UserInvitation(Model):
    __tablename__ = 'user_invitations'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    inviter_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    accepted: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["UserInvitation"]]


class UserFederationAlias(Model):
    __tablename__ = 'fed_user_aliases'

    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    name: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    use_real_name: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    email: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    use_real_email: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    orcid: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    use_real_orcid: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    affiliation: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    use_real_affiliation: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    role: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    use_real_role: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    extra_fields: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False, default={}, server_default=db.text("'{}'::json"))
    last_modified: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    user: Mapped[User] = relationship('User')
    component: Mapped['Component'] = relationship('Component')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["UserFederationAlias"]]

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
            last_modified: typing.Optional[datetime.datetime] = None):
        super().__init__(
            user_id=user_id,
            component_id=component_id,
            name=name,
            use_real_name=use_real_name,
            email=email,
            use_real_email=use_real_email,
            orcid=orcid,
            use_real_orcid=use_real_orcid,
            affiliation=affiliation,
            use_real_affiliation=use_real_affiliation,
            role=role,
            use_real_role=use_real_role,
            extra_fields=extra_fields if extra_fields is not None else {},
            last_modified=last_modified if last_modified is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(user_id={self.user_id}, component_id={self.component_id}; name={self.name})>'


class FederatedIdentity(Model):
    __tablename__ = 'fed_identities'

    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, primary_key=True)
    user: Mapped[User] = relationship('User', foreign_keys=[user_id])
    local_fed_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, primary_key=True)
    local_fed_user: Mapped[User] = relationship('User', foreign_keys=[local_fed_id])
    active: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=True)
    login: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["FederatedIdentity"]]

    def __init__(self, user_id: int, local_fed_id: int, active: bool = True, login: bool = False):
        super().__init__(user_id=user_id, local_fed_id=local_fed_id, active=active, login=login)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(user_id={self.user_id}, local_fed_id={self.local_fed_id}, active={self.active}, login={self.login})>"
