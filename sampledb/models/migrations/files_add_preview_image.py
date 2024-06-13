# coding: utf-8
"""
Add preview_image_binary_data and preview_image_mime_type columns to files table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('files', 'preview_image_binary_data'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE files
        ADD preview_image_binary_data BYTEA NULL,
        ADD preview_image_mime_type VARCHAR NULL
    """))
    return True
