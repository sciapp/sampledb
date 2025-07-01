# coding: utf-8
"""

"""

import datetime
import typing

from sqlalchemy.orm import Query, Mapped, relationship

from .. import db
from .objects import Objects
from .utils import Model

if typing.TYPE_CHECKING:
    from .components import Component
    from .users import User


class File(Model):
    __tablename__ = 'files'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
            name='files_not_null_check'
        ),
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR data IS NOT NULL',
            name='files_not_null_check_data'
        ),
        db.UniqueConstraint('fed_id', 'object_id', 'component_id', name='files_fed_id_component_id_key')
    )

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    user_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    utc_datetime: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    data: Mapped[typing.Optional[typing.Dict[str, typing.Any]]] = db.Column(db.JSON, nullable=True)
    binary_data: Mapped[typing.Optional[bytes]] = db.deferred(db.Column(db.LargeBinary, nullable=True))
    fed_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)
    component_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    uploader: Mapped[typing.Optional['User']] = relationship('User')
    component: Mapped[typing.Optional['Component']] = relationship('Component')
    preview_image_binary_data: Mapped[typing.Optional[bytes]] = db.deferred(db.Column(db.LargeBinary, nullable=True))
    preview_image_mime_type: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["File"]]

    def __init__(
            self,
            file_id: int,
            object_id: int,
            user_id: typing.Optional[int],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            data: typing.Optional[typing.Dict[str, typing.Any]] = None,
            binary_data: typing.Optional[bytes] = None,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None,
            preview_image_binary_data: typing.Optional[bytes] = None,
            preview_image_mime_type: typing.Optional[str] = None,
    ) -> None:
        super().__init__(
            id=file_id,
            object_id=object_id,
            user_id=user_id,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            data=data,
            binary_data=binary_data,
            fed_id=fed_id,
            component_id=component_id,
            preview_image_binary_data=preview_image_binary_data,
            preview_image_mime_type=preview_image_mime_type,
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, object_id={self.object_id}, user_id={self.user_id}, utc_datetime={self.utc_datetime}, data="{self.data}")>'
