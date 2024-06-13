# coding: utf-8
"""
Add last_modified_by_id column to users table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('users', 'last_modified_by_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
        ADD last_modified_by_id INTEGER NULL,
        ADD FOREIGN KEY(last_modified_by_id) REFERENCES users(id);
    """))
    return True
