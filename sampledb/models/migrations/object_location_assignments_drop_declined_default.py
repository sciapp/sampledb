# coding: utf-8
"""
Remove the default value for the declined column in the object location assignments table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 129
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ALTER COLUMN declined DROP DEFAULT
    """))
    return True
