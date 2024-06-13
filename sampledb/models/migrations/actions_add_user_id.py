# coding: utf-8
"""
Add user_id column to actions table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'user_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD user_id INTEGER
    """))
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD FOREIGN KEY(user_id) REFERENCES users(id)
    """))
    return True
