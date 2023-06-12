# coding: utf-8
"""
Add objects_readable_by_all_users_by_default column to actions table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column
from .components_add_discoverable import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'objects_readable_by_all_users_by_default'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD objects_readable_by_all_users_by_default BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
