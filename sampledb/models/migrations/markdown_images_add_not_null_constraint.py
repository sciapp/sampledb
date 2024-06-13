# coding: utf-8
"""
Add missing NOT NULL constraint to column in markdown_images table.
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('markdown_images', 'utc_datetime'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE markdown_images
            ALTER COLUMN utc_datetime SET NOT NULL
    """))
    return True
