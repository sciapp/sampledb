# coding: utf-8
"""
Add user_id column to actions table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    client_column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'actions'
    """)).fetchall()
    if ('user_id',) in client_column_names:
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
