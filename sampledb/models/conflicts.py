import typing

from sqlalchemy.orm import Mapped, Query, relationship

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User


class ObjectVersionConflict(Model):
    __tablename__ = 'object_version_conflicts'

    object_id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    fed_version_id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    component_id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    component: Mapped[typing.Optional['User']] = relationship('User')

    discarded: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    solver_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, default=None)
    version_solved_in: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True, default=None)
    base_version_id: Mapped[int] = db.Column(db.Integer, nullable=False)
    local_version_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True, default=None)
    automerged: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query['ObjectVersionConflict']]

    def __init__(
        self,
        object_id: int,
        fed_version_id: int,
        component_id: int,
        base_version_id: int,
        discarded: bool = False,
        local_version_id: typing.Optional[int] = None,
        solver_id: typing.Optional[int] = None,
        version_solved_in: typing.Optional[int] = None,
        automerged: bool = False
    ) -> None:
        super().__init__(
            object_id=object_id,
            fed_version_id=fed_version_id,
            component_id=component_id,
            base_version_id=base_version_id,
            discarded=discarded,
            local_version_id=local_version_id,
            solver_id=solver_id,
            version_solved_in=version_solved_in,
            automerged=automerged
        )
