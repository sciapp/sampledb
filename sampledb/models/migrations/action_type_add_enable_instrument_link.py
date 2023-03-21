# coding: utf-8
"""
Add the enable_instrument_link column to the action_types table.
"""

import os

import flask_sqlalchemy

from .languages_add_not_null_constraints import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX
from .utils import table_has_column

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('action_types', 'enable_instrument_link'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD enable_instrument_link BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
