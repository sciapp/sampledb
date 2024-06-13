# coding: utf-8
"""
Add short_description column to topics table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('topics', 'short_description'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE topics
        ADD short_description JSON NOT NULL DEFAULT '{}'::json
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        ALTER COLUMN short_description DROP DEFAULT
    """))
    return True
