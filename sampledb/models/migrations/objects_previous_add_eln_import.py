# coding: utf-8
"""
Add eln_import_id and eln_object_id columns to objects_previous table and update NOT NULL constraint.
"""

import os

import flask_sqlalchemy

from .object_log_entry_type_add_import_from_eln_file import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'objects_previous'
    """)).fetchall()
    if ('eln_import_id',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_previous
        ADD eln_import_id INTEGER,
        ADD eln_object_id VARCHAR,
        ADD FOREIGN KEY(eln_import_id) REFERENCES eln_imports(id)
    """))
    db.session.execute(db.text("""
        ALTER TABLE objects_previous
        DROP CONSTRAINT objects_previous_not_null_check
    """))
    db.session.execute(db.text("""
        ALTER TABLE objects_previous
        ADD CONSTRAINT objects_previous_not_null_check
            CHECK (
                (
                    fed_object_id IS NOT NULL AND
                    fed_version_id IS NOT NULL AND
                    component_id IS NOT NULL
                ) OR (
                    eln_import_id IS NOT NULL AND
                    eln_object_id IS NOT NULL
                ) OR (
                    action_id IS NOT NULL AND
                    data IS NOT NULL AND
                    schema IS NOT NULL AND
                    user_id IS NOT NULL AND
                    utc_datetime IS NOT NULL
                )
            )
    """))
    return True
