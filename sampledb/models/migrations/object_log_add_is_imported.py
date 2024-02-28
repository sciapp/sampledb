# coding: utf-8
"""
Add is_imported column to object_log table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column
from .actions_add_use_instrument_topics import MIGRATION_INDEX as PREVIOUS_INDEX

MIGRATION_INDEX = PREVIOUS_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('object_log_entries', 'is_imported'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_log_entries
        ADD is_imported BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
