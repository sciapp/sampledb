# coding: utf-8
"""
Add extra_fields column to users table.
"""

import os

MIGRATION_INDEX = 66
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    client_column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
    """).fetchall()
    if ('extra_fields',) in client_column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE users
        ADD extra_fields JSON NOT NULL DEFAULT '{}'::json
    """)
    return True
