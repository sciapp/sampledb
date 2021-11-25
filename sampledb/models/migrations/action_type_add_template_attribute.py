# coding: utf-8
"""
Add the disable_create_objects column to the action_types table.
"""

import os

MIGRATION_INDEX = 69
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Add column to action_type table
    client_column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'action_types'
    """).fetchall()
    if ('is_template',) in client_column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE action_types
        ADD is_template Boolean DEFAULT false
    """)
    return True
