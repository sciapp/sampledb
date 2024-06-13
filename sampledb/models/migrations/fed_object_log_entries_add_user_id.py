# coding: utf-8
"""
Add user_id column to fed_object_log_entries table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('fed_object_log_entries', 'user_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE fed_object_log_entries
        ADD user_id INTEGER REFERENCES users(id)
    """))
    return True
