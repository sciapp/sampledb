# coding: utf-8
"""

"""

import typing
import datetime

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, Mapped, Query

from .. import db
from .components import Component
from .objects import Objects
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User


class ObjectShare(Model):
    __tablename__ = 'object_shares'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False, primary_key=True)
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Component.id), nullable=False, primary_key=True)
    policy: Mapped[typing.Dict[str, typing.Any]] = db.Column(postgresql.JSONB, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    component: Mapped[Component] = relationship('Component')
    user_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user: Mapped[typing.Optional['User']] = relationship('User')
    import_status: Mapped[typing.Optional[typing.Dict[str, typing.Any]]] = db.Column(postgresql.JSONB)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ObjectShare"]]

    def __init__(
            self,
            object_id: int,
            component_id: int,
            policy: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            user_id: typing.Optional[int] = None
    ) -> None:
        super().__init__(
            object_id=object_id,
            component_id=component_id,
            policy=policy,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            user_id=user_id
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(object_id={self.object_id}, component_id={self.component_id}, policy={self.policy}, utc_datetime={self.utc_datetime})>'


class ObjectImportSpecification(Model):
    __tablename__ = 'object_import_specifications'

    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False, primary_key=True)
    data: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    files: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    action: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    users: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    comments: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    object_location_assignments: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ObjectImportSpecification"]]

    def __init__(
        self,
        object_id: int,
        data: bool,
        files: bool,
        action: bool,
        users: bool,
        comments: bool,
        object_location_assignments: bool
    ):
        super().__init__(
            object_id=object_id,
            data=data,
            files=files,
            action=action,
            users=users,
            comments=comments,
            object_location_assignments=object_location_assignments
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(object_id={self.object_id}, data={self.data}, files={self.files}, action={self.action}, users={self.users}, comments={self.comments}, object_location_assignment={self.object_location_assignments})>'
