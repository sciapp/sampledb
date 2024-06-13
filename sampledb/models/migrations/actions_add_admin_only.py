# coding: utf-8
"""
Add the admin_only column to the actions table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'admin_only'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD admin_only boolean NOT NULL DEFAULT(FALSE)
    """))
    return True
