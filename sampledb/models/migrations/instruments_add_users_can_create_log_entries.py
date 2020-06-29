# coding: utf-8
"""
Add users_can_create_log_entries column to instruments table.
"""

import os

MIGRATION_INDEX = 20
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instruments'
    """).fetchall()
    if ('users_can_create_log_entries',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE instruments
        ADD users_can_create_log_entries BOOLEAN NOT NULL DEFAULT FALSE
    """)
    return True
