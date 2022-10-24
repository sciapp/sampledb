# coding: utf-8
"""
Recreate the markdown_to_html_cache_entries table.
"""

import os

import flask_sqlalchemy

from ..markdown_to_html_cache import MarkdownToHTMLCacheEntry

MIGRATION_INDEX = 42
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'markdown_to_html_cache_entries'
    """)).fetchall()
    if ('parameters',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        DROP TABLE markdown_to_html_cache_entries
    """))
    db.session.commit()

    MarkdownToHTMLCacheEntry.__table__.create(bind=db.engine)

    return True
