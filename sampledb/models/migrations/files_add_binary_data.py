# coding: utf-8
"""
Add binary data column to files table.
"""

import os

MIGRATION_INDEX = 67
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'files'
    """).fetchall()
    if ('binary_data',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE files
        ADD binary_data BYTEA NULL
    """)
    return True
