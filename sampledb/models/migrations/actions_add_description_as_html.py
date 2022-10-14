# coding: utf-8
"""
Add description_as_html column to actions table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 15
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'actions'
    """)).fetchall()
    if ('description_as_html',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD description_as_html TEXT NULL
    """))
    return True
