# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from .objects import Objects


class File(db.Model):  # type: ignore
    __tablename__ = 'files'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
            name='files_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'object_id', 'component_id', name='files_fed_id_component_id_key')
    )

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    utc_datetime = db.Column(db.DateTime, nullable=True)
    data = db.Column(db.JSON, nullable=True)
    binary_data = db.deferred(db.Column(db.LargeBinary, nullable=True))
    fed_id = db.Column(db.Integer, nullable=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    uploader = db.relationship('User')
    component = db.relationship('Component')

    def __init__(
            self,
            file_id: int,
            object_id: int,
            user_id: typing.Optional[int],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            data: typing.Optional[typing.Dict[str, typing.Any]] = None,
            binary_data: typing.Optional[bytes] = None,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None
    ) -> None:
        self.id = file_id
        self.object_id = object_id
        self.user_id = user_id
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.data = data
        self.binary_data = binary_data
        self.fed_id = fed_id
        self.component_id = component_id

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, object_id={1.object_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, data="{1.data}")>'.format(type(self).__name__, self)
