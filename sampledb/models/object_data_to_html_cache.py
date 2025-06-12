# coding: utf-8
"""

"""
import typing

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, Query

from .. import db
from .utils import Model


class ObjectDataToHTMLCacheEntry(Model):
    __tablename__ = 'object_data_to_html_cache_entries'

    object_id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    version_id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_language: Mapped[str] = db.Column(db.String, primary_key=True)
    metadata_language: Mapped[str] = db.Column(db.String, primary_key=True)
    timezone: Mapped[str] = db.Column(db.String, primary_key=True)
    workflow_display_mode: Mapped[bool] = db.Column(db.Boolean, primary_key=True)

    html: Mapped[str] = db.Column(db.Text, nullable=False)
    object_dependencies: Mapped[typing.List[typing.Tuple[int, typing.Optional[str], typing.Optional[int]]]] = db.Column(postgresql.JSONB, nullable=False)
    user_dependencies: Mapped[typing.List[typing.Tuple[int, typing.Optional[int], typing.Optional[str]]]] = db.Column(postgresql.JSONB, nullable=False)
    component_dependencies: Mapped[typing.List[typing.Tuple[str, typing.Optional[int], typing.Optional[str], typing.Optional[str]]]] = db.Column(postgresql.JSONB, nullable=False)
    file_dependencies: Mapped[typing.List[typing.Tuple[int, int, typing.Optional[str], typing.Optional[bool], typing.Optional[str]]]] = db.Column(postgresql.JSONB, nullable=False)
    id_prefix_root_placeholder: Mapped[str] = db.Column(db.String, nullable=False)
    hashes_to_replace: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSONB, nullable=False)

    cache_hit_counter: Mapped[int] = db.Column(db.Integer, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ObjectDataToHTMLCacheEntry"]]
