# coding: utf-8
"""
Add create_log_entry_default column to instruments table.
"""

import os

MIGRATION_INDEX = 25
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instruments'
    """).fetchall()
    if ('create_log_entry_default',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE instruments
        ADD create_log_entry_default BOOLEAN NOT NULL DEFAULT FALSE
    """)
    return True
