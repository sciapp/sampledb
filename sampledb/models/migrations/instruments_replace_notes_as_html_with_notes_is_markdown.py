# coding: utf-8
"""
Replace notes_as_html column with notes_is_markdown in instruments table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 39
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instruments'
    """)).fetchall()
    if ('notes_is_markdown',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD notes_is_markdown BOOLEAN NOT NULL DEFAULT FALSE
    """))
    db.session.execute(db.text("""
        UPDATE instruments
        SET notes_is_markdown = TRUE
        WHERE notes_as_html IS NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE instruments
        DROP notes_as_html
    """))
    return True
