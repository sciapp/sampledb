# coding: utf-8
"""
Add extra_fields column to users table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('users', 'extra_fields'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
        ADD extra_fields JSON NOT NULL DEFAULT '{}'::json
    """))
    return True
