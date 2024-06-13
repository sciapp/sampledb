# coding: utf-8
"""
Add fed_id and component_id columns to files table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('files', 'fed_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE files
            ADD fed_id INTEGER,
            ADD component_id INTEGER,
            ADD FOREIGN KEY(component_id) REFERENCES components(id),
            ADD CONSTRAINT files_fed_id_component_id_key UNIQUE(fed_id, object_id, component_id)
    """))
    return True
