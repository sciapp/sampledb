# coding: utf-8
"""
Add last_sync_timestamp column to components table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 113
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('components', 'last_sync_timestamp'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE components
            ADD last_sync_timestamp TIMESTAMP WITHOUT TIME ZONE
    """))
    return True
