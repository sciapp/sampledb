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
    from .components import Component


@enum.unique
class ComponentAuthenticationType(enum.Enum):
    TOKEN = 1


class ComponentAuthentication(Model):
    __tablename__ = "component_authentications"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    login: Mapped[typing.Dict[str, typing.Any]] = db.Column(postgresql.JSONB, nullable=False)
    type: Mapped[ComponentAuthenticationType] = db.Column(db.Enum(ComponentAuthenticationType), nullable=False)
    component: Mapped['Component'] = relationship('Component')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ComponentAuthentication"]]

    def __init__(
            self,
            login: typing.Dict[str, typing.Any],
            authentication_type: ComponentAuthenticationType,
            component_id: int
    ) -> None:
        super().__init__(
            component_id=component_id,
            login=login,
            type=authentication_type
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id})>'


class OwnComponentAuthentication(Model):
    __tablename__ = "own_component_authentications"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    login: Mapped[typing.Dict[str, typing.Any]] = db.Column(postgresql.JSONB, nullable=False)
    type: Mapped[ComponentAuthenticationType] = db.Column(db.Enum(ComponentAuthenticationType), nullable=False)
    component: Mapped['Component'] = relationship('Component')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["OwnComponentAuthentication"]]

    def __init__(
            self,
            login: typing.Dict[str, typing.Any],
            authentication_type: ComponentAuthenticationType,
            component_id: int
    ) -> None:
        super().__init__(
            component_id=component_id,
            login=login,
            type=authentication_type
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id})>'
