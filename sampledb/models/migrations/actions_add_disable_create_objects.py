# coding: utf-8
"""
Add the disable_create_objects column to the actions table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 121
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    client_column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'actions'
    """)).fetchall()
    if ('disable_create_objects',) in client_column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD disable_create_objects boolean NOT NULL DEFAULT(FALSE)
    """))
    return True
