# coding: utf-8
"""
Add fed_object_id column to objects_previous table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 73
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'objects_previous'
    """)).fetchall()
    if ('fed_object_id',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_previous
            ADD fed_object_id INTEGER,
            ADD fed_version_id INTEGER,
            ADD component_id INTEGER,
            ADD FOREIGN KEY(component_id) REFERENCES components(id)
    """))
    return True
