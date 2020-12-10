# coding: utf-8
"""

"""

from .. import db


class MarkdownToHTMLCacheEntry(db.Model):
    __tablename__ = 'markdown_to_html_cache_entries'

    markdown = db.Column(db.Text, primary_key=True)
    html = db.Column(db.Text, nullable=False)
