# coding: utf-8
"""
Add content_is_markdown column to instrument_log_entry_versions table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 46
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instrument_log_entry_versions'
    """)).fetchall()
    if ('content_is_markdown',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instrument_log_entry_versions
        ADD content_is_markdown BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
