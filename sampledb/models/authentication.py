# coding: utf-8
"""

"""

import enum
import typing

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, Query, Mapped

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User


@enum.unique
class AuthenticationType(enum.Enum):
    LDAP = 1
    EMAIL = 2
    OTHER = 3
    API_TOKEN = 4
    API_ACCESS_TOKEN = 5


class Authentication(Model):
    __tablename__ = "authentications"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    login: Mapped[typing.Dict[str, typing.Any]] = db.Column(postgresql.JSONB, nullable=False)
    type: Mapped[AuthenticationType] = db.Column(db.Enum(AuthenticationType), nullable=False)
    confirmed: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    user: Mapped['User'] = relationship('User', back_populates="authentication_methods")

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Authentication"]]

    def __init__(
            self,
            login: typing.Dict[str, typing.Any],
            authentication_type: AuthenticationType,
            confirmed: bool,
            user_id: int
    ) -> None:
        super().__init__(
            user_id=user_id,
            login=login,
            type=authentication_type,
            confirmed=confirmed
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id})>'


class TwoFactorAuthenticationMethod(Model):
    __tablename__ = "two_factor_authentication_methods"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    active: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(postgresql.JSONB, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["TwoFactorAuthenticationMethod"]]
