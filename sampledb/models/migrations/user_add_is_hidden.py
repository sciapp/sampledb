# coding: utf-8
"""
Add is_hidden column to users table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('users', 'is_hidden'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
        ADD is_hidden BOOLEAN NOT NULL DEFAULT(FALSE)
    """))
    return True
