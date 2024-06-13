# coding: utf-8
"""
Add fed_object_id column to objects_previous table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('objects_previous', 'fed_object_id'):
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
