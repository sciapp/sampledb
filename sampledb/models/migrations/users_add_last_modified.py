# coding: utf-8
"""
Add last_modified column to users table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 114
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('users', 'last_modified'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
        ADD last_modified TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc');
        ALTER TABLE users
        ALTER COLUMN last_modified DROP DEFAULT;
    """))
    return True
