# coding: utf-8
"""
Add last_sync_timestamp column to components table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 113
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'components'
    """)).fetchall()
    if ('last_sync_timestamp',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE components
            ADD last_sync_timestamp TIMESTAMP WITHOUT TIME ZONE
    """))
    return True
