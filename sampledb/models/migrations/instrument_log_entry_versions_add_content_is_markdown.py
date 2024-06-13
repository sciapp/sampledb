# coding: utf-8
"""
Add content_is_markdown column to instrument_log_entry_versions table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instrument_log_entry_versions', 'content_is_markdown'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instrument_log_entry_versions
        ADD content_is_markdown BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
