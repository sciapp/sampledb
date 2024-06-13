# coding: utf-8
"""
Add name_cache column to objects_current table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('objects_current', 'name_cache'):
        return False

    # Perform migration
    db.session.execute(db.text("""
    ALTER TABLE objects_current
    ADD COLUMN name_cache JSON NULL
    """))
    db.session.execute(db.text("""
    UPDATE objects_current
    SET name_cache = data -> 'name' -> 'text'
    """))
    return True
