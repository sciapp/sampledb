# coding: utf-8
"""
Add tags_cache column to objects_current table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 94
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'objects_current'
    """)).fetchall()
    if ('tags_cache',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
    ALTER TABLE objects_current
    ADD COLUMN tags_cache JSON NULL
    """))
    db.session.execute(db.text("""
    UPDATE objects_current
    SET tags_cache = data -> 'tags'
    """))
    return True
