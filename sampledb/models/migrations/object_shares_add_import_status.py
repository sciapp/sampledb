# coding: utf-8
"""
Add import_status column to object_shares table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 138
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'object_shares'
    """)).fetchall()
    if ('import_status',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_shares
        ADD import_status JSONB
    """))
    return True
