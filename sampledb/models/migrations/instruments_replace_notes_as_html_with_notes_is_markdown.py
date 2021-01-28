# coding: utf-8
"""
Replace notes_as_html column with notes_is_markdown in instruments table.
"""

import os

MIGRATION_INDEX = 39
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instruments'
    """).fetchall()
    if ('notes_is_markdown',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE instruments
        ADD notes_is_markdown BOOLEAN NOT NULL DEFAULT FALSE
    """)
    db.session.execute("""
        UPDATE instruments
        SET notes_is_markdown = TRUE
        WHERE notes_as_html IS NOT NULL
    """)
    db.session.execute("""
        ALTER TABLE instruments
        DROP notes_as_html
    """)
    return True
