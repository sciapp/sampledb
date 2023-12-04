# coding: utf-8
"""

"""

import datetime
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .components import Component
from .users import User
from .utils import Model


class MarkdownImage(Model):
    __tablename__ = 'markdown_images'
    __table_args__ = (
        db.UniqueConstraint('file_name', 'component_id', name='markdown_images_file_name_component_id_key'),
    )

    file_name: Mapped[str] = db.Column(db.Text, nullable=False)
    content: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)
    user_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    permanent: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    component_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey(Component.id), nullable=True)
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["MarkdownImage"]]

    def __init__(
            self,
            file_name: str,
            content: bytes,
            user_id: typing.Optional[int],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            permanent: typing.Optional[bool] = False,
            component_id: typing.Optional[int] = None
    ) -> None:
        super().__init__(
            file_name=file_name,
            content=content,
            user_id=user_id,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            permanent=permanent,
            component_id=component_id
        )
