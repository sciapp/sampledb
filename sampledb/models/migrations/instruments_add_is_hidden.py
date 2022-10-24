# coding: utf-8
"""
Add is_hidden column to instruments table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 28
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    client_column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instruments'
    """)).fetchall()
    if ('is_hidden',) in client_column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD is_hidden BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
