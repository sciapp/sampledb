# coding: utf-8
"""

"""

import datetime
import typing

from sqlalchemy.orm import relationship, Mapped, Query

from .. import db
from .objects import Objects
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User
    from .components import Component


class Comment(Model):
    __tablename__ = 'comments'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
            name='comments_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='comments_fed_id_component_id_key')
    )

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    author: Mapped[typing.Optional['User']] = relationship('User')
    content: Mapped[str] = db.Column(db.Text, nullable=False)
    utc_datetime: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    fed_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)
    component_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component: Mapped[typing.Optional['Component']] = relationship('Component')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Comment"]]

    def __init__(
            self,
            object_id: int,
            user_id: typing.Optional[int],
            content: str,
            utc_datetime: typing.Optional[datetime.datetime] = None,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None
    ) -> None:
        super().__init__(
            object_id=object_id,
            user_id=user_id,
            content=content,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            fed_id=fed_id,
            component_id=component_id
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, object_id={self.object_id}, user_id={self.user_id}, utc_datetime={self.utc_datetime}, content="{self.content}")>'
