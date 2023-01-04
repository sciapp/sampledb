# coding: utf-8
"""
Add user_id column to fed_object_log_entries table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 135
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'fed_object_log_entries'
    """)).fetchall()
    if ('user_id',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE fed_object_log_entries
        ADD user_id INTEGER REFERENCES users(id)
    """))
    return True
