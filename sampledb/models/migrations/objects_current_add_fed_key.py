# coding: utf-8
"""
Add fed_object_id, fed_version_id and component_id columns to objects_current table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('objects_current', 'fed_object_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_current
            ADD fed_object_id INTEGER,
            ADD fed_version_id INTEGER,
            ADD component_id INTEGER,
            ADD FOREIGN KEY(component_id) REFERENCES components(id),
            ADD CONSTRAINT objects_current_fed_object_id_component_id_key UNIQUE(fed_object_id, fed_version_id, component_id)
    """))
    return True
