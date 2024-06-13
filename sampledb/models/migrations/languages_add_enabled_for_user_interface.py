# coding: utf-8
"""
Add enabled_for_user_interface column to languages table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('languages', 'enabled_for_user_interface'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE languages
        ADD enabled_for_user_interface BOOLEAN DEFAULT FALSE NOT NULL
    """))
    db.session.execute(db.text("""
        UPDATE languages
        SET enabled_for_user_interface = TRUE
        WHERE id < 0
    """))
    return True
