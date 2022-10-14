# coding: utf-8
"""
Add the disable_create_objects column to the action_types table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 69
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Add column to action_type table
    client_column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'action_types'
    """)).fetchall()
    if ('is_template',) in client_column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD is_template boolean NOT NULL DEFAULT(FALSE)
    """))
    return True
