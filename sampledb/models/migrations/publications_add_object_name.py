# coding: utf-8
"""
Add object_name column to object_publications table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 27
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('object_publications', 'object_name'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_publications
        ADD object_name TEXT NULL
    """))
    return True
