# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from .components import Component
from .users import User


class MarkdownImage(db.Model):  # type: ignore
    __tablename__ = 'markdown_images'
    __table_args__ = (
        db.UniqueConstraint('file_name', 'component_id', name='markdown_images_file_name_component_id_key'),
    )

    file_name = db.Column(db.Text, nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    utc_datetime = db.Column(db.DateTime, nullable=True)
    permanent = db.Column(db.Boolean, nullable=False, default=False)
    component_id = db.Column(db.Integer, db.ForeignKey(Component.id), nullable=True)
    id = db.Column(db.Integer, primary_key=True)

    def __init__(
            self,
            file_name: str,
            content: bytes,
            user_id: typing.Optional[int],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            permanent: typing.Optional[bool] = False,
            component_id: typing.Optional[int] = None
    ) -> None:
        self.file_name = file_name
        self.content = content
        self.user_id = user_id
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.permanent = permanent
        self.component_id = component_id
