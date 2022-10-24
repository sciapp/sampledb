# coding: utf-8
"""
Add binary data column to files table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 67
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'files'
    """)).fetchall()
    if ('binary_data',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE files
        ADD binary_data BYTEA NULL
    """))
    return True
