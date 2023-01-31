# coding: utf-8
"""
Add import_status column to object_shares table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 138
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('object_shares', 'import_status'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_shares
        ADD import_status JSONB
    """))
    return True
