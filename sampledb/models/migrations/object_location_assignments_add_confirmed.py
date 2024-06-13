# coding: utf-8
"""
Add confirmed column to object location assignments table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('object_location_assignments', 'confirmed'):
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
