# coding: utf-8
"""
Add users_can_create_log_entries column to instruments table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 20
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'users_can_create_log_entries'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD users_can_create_log_entries BOOLEAN NOT NULL DEFAULT FALSE
    """))
    return True
