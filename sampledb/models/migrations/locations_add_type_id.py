# coding: utf-8
"""
Add type_id column to locations table and set default location type.
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..locations import LocationType


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('locations', 'type_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE locations
            ADD type_id INTEGER NULL,
            ADD FOREIGN KEY(type_id) REFERENCES location_types(id)
    """))

    db.session.execute(db.text("""
        UPDATE locations
        SET type_id = :type_id
        WHERE type_id IS NULL
    """), params={
        'type_id': LocationType.LOCATION
    })

    db.session.execute(db.text("""
        ALTER TABLE locations
        ALTER type_id SET NOT NULL
    """))
    return True
