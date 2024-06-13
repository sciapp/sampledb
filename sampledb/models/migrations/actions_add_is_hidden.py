# coding: utf-8
"""
Add is_hidden column to actions table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'is_hidden'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD is_hidden BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
