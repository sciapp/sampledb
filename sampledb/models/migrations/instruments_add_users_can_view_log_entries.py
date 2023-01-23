# coding: utf-8
"""
Add users_can_view_log_entries column to instruments table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 21
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instruments'
    """)).fetchall()
    if ('users_can_view_log_entries',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD users_can_view_log_entries BOOLEAN NOT NULL DEFAULT FALSE
    """))
    return True
