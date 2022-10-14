# coding: utf-8
"""
Add extra_fields column to users table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 66
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    client_column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
    """)).fetchall()
    if ('extra_fields',) in client_column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
        ADD extra_fields JSON NOT NULL DEFAULT '{}'::json
    """))
    return True
