# coding: utf-8
"""
Add binary data column to files table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 67
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('files', 'binary_data'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE files
        ADD binary_data BYTEA NULL
    """))
    return True
