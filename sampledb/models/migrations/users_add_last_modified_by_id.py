# coding: utf-8
"""
Add last_modified_by_id column to users table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 122
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    users_column_names = db.session.execute(db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
        """)).fetchall()
    if ('last_modified_by_id',) in users_column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
        ADD last_modified_by_id INTEGER NULL,
        ADD FOREIGN KEY(last_modified_by_id) REFERENCES users(id);
    """))
    return True
