# coding: utf-8
"""
Add user_id column to object_shares table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 136
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('object_shares', 'user_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_shares
        ADD user_id INTEGER REFERENCES users(id)
    """))
    return True
