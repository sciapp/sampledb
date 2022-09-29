# coding: utf-8
"""
Add last_modified_by_id column to users table.
"""

import os

MIGRATION_INDEX = 122
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    users_column_names = db.session.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
        """).fetchall()
    if ('last_modified_by_id',) in users_column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE users
        ADD last_modified_by_id INTEGER NULL,
        ADD FOREIGN KEY(last_modified_by_id) REFERENCES users(id);
    """)
    return True
