# coding: utf-8
"""
Drop the description column from the action_types table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 60
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('action_types', 'description'):
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE action_types
            DROP COLUMN description
        """))

    return True
