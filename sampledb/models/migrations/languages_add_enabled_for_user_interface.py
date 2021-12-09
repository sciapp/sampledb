# coding: utf-8
"""
Add enabled_for_user_interface column to languages table.
"""

import os

MIGRATION_INDEX = 59
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    languages_column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'languages'
    """).fetchall()
    if ('enabled_for_user_interface',) in languages_column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE languages
        ADD enabled_for_user_interface BOOLEAN DEFAULT FALSE NOT NULL
    """)
    db.session.execute("""
        UPDATE languages
        SET enabled_for_user_interface = TRUE
        WHERE id < 0
    """)
    return True
