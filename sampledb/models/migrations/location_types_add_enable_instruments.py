# coding: utf-8
"""
Add enable_instruments to location_types table.
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..locations import LocationType


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('location_types', 'enable_instruments'):
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
