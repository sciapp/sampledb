"""
Add column version_component_id to table objects_current. Update check constraint.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column("objects_current", "version_component_id"):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_current
        ADD COLUMN version_component_id INTEGER,
        ADD FOREIGN KEY(version_component_id) REFERENCES components(id)
    """))

    db.session.execute(db.text("""
        UPDATE objects_current
        SET version_component_id = component_id
    """))

    db.session.execute(db.text("""
        ALTER TABLE objects_current
        DROP CONSTRAINT objects_current_not_null_check
    """))

    db.session.execute(db.text("""
        ALTER TABLE objects_current
        ADD CONSTRAINT objects_current_not_null_check
        CHECK (
            (
                fed_object_id IS NOT NULL AND
                component_id IS NOT NULL
            ) OR (
                version_component_id IS NOT NULL
            ) OR (
                eln_import_id IS NOT NULL AND
                eln_object_id IS NOT NULL
            ) OR (
                action_id IS NOT NULL AND
                data IS NOT NULL AND
                schema IS NOT NULL AND
                utc_datetime IS NOT NULL
            )
        )
    """))
    return True
