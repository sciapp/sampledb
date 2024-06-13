# coding: utf-8
"""
Add role column to users table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('users', 'role'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
        ADD role TEXT NULL
    """))
    return True
