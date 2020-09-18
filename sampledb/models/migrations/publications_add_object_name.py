# coding: utf-8
"""
Add object_name column to object_publications table.
"""

import os

MIGRATION_INDEX = 27
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'object_publications'
    """).fetchall()
    if ('object_name',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE object_publications
        ADD object_name TEXT NULL
    """)
    return True
