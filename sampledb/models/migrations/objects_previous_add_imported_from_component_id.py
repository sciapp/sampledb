"""
Add column imported_from_component_id to table objects_previous.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column("objects_previous", "imported_from_component_id"):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_previous
        ADD COLUMN imported_from_component_id INTEGER,
        ADD FOREIGN KEY(imported_from_component_id) REFERENCES components(id)
    """))
    return True
