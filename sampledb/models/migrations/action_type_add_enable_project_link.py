# coding: utf-8
"""
Add the enable_project_link column to the action_types table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 43
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('action_types', 'enable_project_link'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD enable_project_link BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
