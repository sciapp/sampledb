# coding: utf-8
"""
Replace description_as_html column with description_is_markdown in actions table.
"""

import os

MIGRATION_INDEX = 37
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'actions'
    """).fetchall()
    if ('description_is_markdown',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE actions
        ADD description_is_markdown BOOLEAN NOT NULL DEFAULT FALSE
    """)
    db.session.execute("""
        UPDATE actions
        SET description_is_markdown = TRUE
        WHERE description_as_html IS NOT NULL
    """)
    db.session.execute("""
        ALTER TABLE actions
        DROP description_as_html
    """)
    return True
