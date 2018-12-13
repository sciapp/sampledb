# coding: utf-8
"""
Add responsible_user_id column to object location assignments table and make location_id nullable.
"""

import os

MIGRATION_INDEX = 6
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'object_location_assignments'
    """).fetchall()
    if ('responsible_user_id',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE object_location_assignments
        ADD responsible_user_id INTEGER
    """)
    db.session.execute("""
        ALTER TABLE object_location_assignments
        ADD FOREIGN KEY(responsible_user_id) REFERENCES users(id)
    """)
    db.session.execute("""
        ALTER TABLE object_location_assignments
        ALTER COLUMN location_id DROP NOT NULL
    """)
    return True
