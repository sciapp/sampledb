# coding: utf-8
"""
Add notes column to instruments table.
"""

import os

MIGRATION_INDEX = 22
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instruments'
    """).fetchall()
    if ('notes',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE instruments
        ADD notes TEXT NOT NULL DEFAULT ''
    """)
    return True
