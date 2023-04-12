# coding: utf-8
"""
Add is_hidden column to instruments table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 28
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'is_hidden'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD is_hidden BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
