# coding: utf-8
"""
Add last_sync_timestamp column to components table.
"""

import os

MIGRATION_INDEX = 113
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'components'
    """).fetchall()
    if ('last_sync_timestamp',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE components
            ADD last_sync_timestamp TIMESTAMP WITHOUT TIME ZONE
    """)
    return True
