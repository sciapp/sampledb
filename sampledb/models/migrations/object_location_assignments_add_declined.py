# coding: utf-8
"""
Add declined column to object location assignments table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 111
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'object_location_assignments'
    """)).fetchall()
    if ('declined',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ADD declined BOOLEAN DEFAULT FALSE NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ADD CONSTRAINT object_location_assignments_not_both_states_check
            CHECK (
                NOT (confirmed AND declined)
            )
    """))
    return True
