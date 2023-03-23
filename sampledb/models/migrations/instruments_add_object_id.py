# coding: utf-8
"""
Add object_id column to instruments table.
"""

import os

import flask_sqlalchemy

from .action_type_add_enable_instrument_link import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX
from .utils import table_has_column

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'object_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
            ADD object_id INTEGER,
            ADD FOREIGN KEY(object_id) REFERENCES objects_current(object_id)
    """))
    return True
