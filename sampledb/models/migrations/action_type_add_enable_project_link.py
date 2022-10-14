# coding: utf-8
"""
Add the enable_project_link column to the action_types table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 43
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'action_types'
    """)).fetchall()
    if ('enable_project_link',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD enable_project_link BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
