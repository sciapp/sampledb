# coding: utf-8
"""
Add users_can_view_log_entries column to instruments table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'users_can_view_log_entries'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD users_can_view_log_entries BOOLEAN NOT NULL DEFAULT FALSE
    """))
    return True
