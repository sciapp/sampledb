# coding: utf-8
"""
Drop the notes column from the instruments table that might have been created by migration 22.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 130
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instruments'
    """)).fetchall()
    if ('notes',) not in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
            DROP COLUMN notes
    """))
    return True
