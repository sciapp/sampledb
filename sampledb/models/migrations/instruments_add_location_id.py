# coding: utf-8
"""
Add location_id column to instruments table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 127
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'location_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
            ADD location_id INTEGER,
            ADD FOREIGN KEY(location_id) REFERENCES locations(id)
    """))
    return True
