# coding: utf-8
"""

"""

from .. import db
import sqlalchemy.dialects.postgresql as postgresql


class MarkdownToHTMLCacheEntry(db.Model):
    __tablename__ = 'markdown_to_html_cache_entries'

    id = db.Column(db.Integer, primary_key=True)
    markdown = db.Column(db.Text, nullable=False)
    parameters = db.Column(postgresql.JSONB, nullable=False)
    html = db.Column(db.Text, nullable=False)
