# coding: utf-8
"""
Add last_modified column to users table.
"""

import os

MIGRATION_INDEX = 114
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    users_column_names = db.session.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
        """).fetchall()
    if ('last_modified',) in users_column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE users
        ADD last_modified TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc');
        ALTER TABLE users
        ALTER COLUMN last_modified DROP DEFAULT;
    """)
    return True
