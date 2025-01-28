# coding: utf-8
"""
Add enable_object_assignments column to locations table and set it to True for existing locations.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('locations', 'enable_object_assignments'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE locations
            ADD enable_object_assignments BOOLEAN DEFAULT TRUE NOT NULL
    """))
    return True
