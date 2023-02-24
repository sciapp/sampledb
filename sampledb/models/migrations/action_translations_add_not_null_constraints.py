# coding: utf-8
"""
Add missing NOT NULL constraints to foreign key columns in action_translations table.
"""

import os

import flask_sqlalchemy

from .location_types_add_enable_capacities import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX
from .utils import column_is_nullable

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('action_translations', 'action_id') and not column_is_nullable('action_translations', 'language_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_translations
            ALTER COLUMN action_id SET NOT NULL,
            ALTER COLUMN language_id SET NOT NULL
    """))
    return True
