# coding: utf-8
"""
Add enable_instruments to location_types table.
"""

import os

import flask_sqlalchemy

from ..locations import LocationType

MIGRATION_INDEX = 126
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'location_types'
    """)).fetchall()
    if ('enable_instruments',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE location_types
            ADD enable_instruments BOOLEAN NOT NULL DEFAULT false
    """))
    db.session.execute(db.text("""
        UPDATE location_types
            SET enable_instruments = true
            WHERE id = :default_type_id
    """), params={'default_type_id': LocationType.LOCATION})
    db.session.execute(db.text("""
        ALTER TABLE location_types
            ALTER COLUMN enable_instruments DROP DEFAULT
    """))
    return True
