# coding: utf-8
"""
Add discoverable column to components table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column
from .user_log_entry_type_add_import_from_eln_file import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('components', 'discoverable'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE components
            ADD discoverable BOOLEAN NOT NULL DEFAULT true
    """))
    return True
