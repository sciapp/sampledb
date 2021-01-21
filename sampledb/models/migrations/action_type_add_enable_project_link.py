# coding: utf-8
"""
Add the enable_project_link column to the action_types table.
"""

import os

MIGRATION_INDEX = 43
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'action_types'
    """).fetchall()
    if ('enable_project_link',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE action_types
        ADD enable_project_link BOOLEAN DEFAULT FALSE NOT NULL
    """)
    return True
