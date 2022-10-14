# coding: utf-8
"""
Add confirmed column to object location assignments table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 11
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'object_location_assignments'
    """)).fetchall()
    if ('confirmed',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ADD confirmed BOOLEAN
    """))
    db.session.execute(db.text("""
        UPDATE object_location_assignments
        SET confirmed = FALSE
        WHERE confirmed IS NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ALTER COLUMN confirmed SET NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ALTER COLUMN confirmed SET DEFAULT FALSE
    """))
    return True
