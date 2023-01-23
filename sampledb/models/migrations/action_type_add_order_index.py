# coding utf-8
"""
Add the order_index column to the action_types table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 119
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'action_types'
    """)).fetchall()
    if ('order_index',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD order_index INTEGER NULL
    """))
    return True
