# coding: utf-8
"""
Drop the description column from the action_types table.
"""

import os

MIGRATION_INDEX = 60
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'action_types'
        """).fetchall()
    if ('description', ) not in column_names:
        return False

    # Perform migration
    db.session.execute("""
            ALTER TABLE action_types
            DROP COLUMN description
        """)

    return True
