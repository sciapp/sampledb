# coding: utf-8
"""
Add affiliation column to users table.
"""

import os

MIGRATION_INDEX = 24
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    client_column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
    """).fetchall()
    if ('affiliation',) in client_column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE users
        ADD affiliation TEXT NULL
    """)
    return True
