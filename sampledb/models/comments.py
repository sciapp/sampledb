# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from .objects import Objects


class Comment(db.Model):  # type: ignore
    __tablename__ = 'comments'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
            name='comments_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='comments_fed_id_component_id_key')
    )

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=True)
    fed_id = db.Column(db.Integer, nullable=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component = db.relationship('Component')

    def __init__(
            self,
            object_id: int,
            user_id: typing.Optional[int],
            content: str,
            utc_datetime: typing.Optional[datetime.datetime] = None,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None
    ) -> None:
        self.object_id = object_id
        self.user_id = user_id
        self.content = content
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.fed_id = fed_id
        self.component_id = component_id

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, object_id={1.object_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, content="{1.content}")>'.format(type(self).__name__, self)
