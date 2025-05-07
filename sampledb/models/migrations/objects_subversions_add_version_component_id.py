"""
Add column version_component_id to table objects_subversions.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column("objects_subversions", "version_component_id"):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_subversions
        ADD COLUMN version_component_id INTEGER,
        ADD FOREIGN KEY(version_component_id) REFERENCES components(id)
    """))

    db.session.execute(db.text("""
        UPDATE objects_subversions
        SET version_component_id = (SELECT component_id FROM objects_current WHERE object_id = objects_subversions.object_id)
    """))
    return True
