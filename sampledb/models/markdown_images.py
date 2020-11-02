# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from .users import User


class MarkdownImage(db.Model):
    __tablename__ = 'markdown_images'

    file_name = db.Column(db.Text, primary_key=True)
    content = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    utc_datetime = db.Column(db.DateTime, nullable=True)
    permanent = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, file_name: str, content: bytes, user_id: int, utc_datetime: typing.Optional[datetime.datetime] = None, permanent: typing.Optional[bool] = False):
        self.file_name = file_name
        self.content = content
        self.user_id = user_id
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime
        self.permanent = permanent
