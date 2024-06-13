# coding: utf-8
"""
Recreate the markdown_to_html_cache_entries table.
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..markdown_to_html_cache import MarkdownToHTMLCacheEntry


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('markdown_to_html_cache_entries', 'parameters'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        DROP TABLE markdown_to_html_cache_entries
    """))
    db.session.commit()

    MarkdownToHTMLCacheEntry.__table__.create(bind=db.engine)  # type: ignore[attr-defined]

    return True
