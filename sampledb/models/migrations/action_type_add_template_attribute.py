# coding: utf-8
"""
Add the disable_create_objects column to the action_types table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 69
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('action_types', 'is_template'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD is_template boolean NOT NULL DEFAULT(FALSE)
    """))
    return True
