# coding: utf-8
"""
Remove NOT NULL constraints for utc_datetime column as intended by migration 85.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 131
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ALTER COLUMN utc_datetime DROP NOT NULL
    """))
    return True
