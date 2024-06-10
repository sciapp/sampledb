# coding: utf-8
"""
Add responsible_user_id column to object location assignments table and make location_id nullable.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('object_location_assignments', 'responsible_user_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ADD responsible_user_id INTEGER
    """))
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ADD FOREIGN KEY(responsible_user_id) REFERENCES users(id)
    """))
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ALTER COLUMN location_id DROP NOT NULL
    """))
    return True
