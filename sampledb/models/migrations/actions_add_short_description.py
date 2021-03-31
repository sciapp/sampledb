# coding: utf-8
"""
Add short_description and short_description_is_markdown columns to actions table.
"""

import os

MIGRATION_INDEX = 41
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'actions'
    """).fetchall()
    if ('short_description',) in column_names:
        return False
    if ('name',) not in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE actions
        ADD short_description TEXT NOT NULL DEFAULT ''
    """)
    db.session.execute("""
        ALTER TABLE actions
        ADD short_description_is_markdown BOOLEAN NOT NULL DEFAULT FALSE
    """)
    db.session.execute("""
        UPDATE actions
        SET short_description = description, short_description_is_markdown=description_is_markdown
    """)
    return True
