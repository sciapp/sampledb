# coding: utf-8
"""

"""
import typing

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, Query

from .. import db
from .utils import Model


class MarkdownToHTMLCacheEntry(Model):
    __tablename__ = 'markdown_to_html_cache_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    markdown: Mapped[str] = db.Column(db.Text, nullable=False)
    parameters: Mapped[typing.Dict[str, typing.Any]] = db.Column(postgresql.JSONB, nullable=False)
    html: Mapped[str] = db.Column(db.Text, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["MarkdownToHTMLCacheEntry"]]
