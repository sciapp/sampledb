# coding: utf-8
"""
Add NOT NULL constraint for data unless fed_id and component_id are not null.
"""

import os

import flask_sqlalchemy

from .actions_add_objects_readable_by_all_users_by_default import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    constraints = db.session.execute(db.text("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'files_not_null_check_data'
    """)).fetchall()

    if len(constraints) > 0:
        return False

    db.session.execute(db.text("""
            UPDATE files SET data = '{"storage": "local", "original_file_name": ""}'::json WHERE data IS NULL AND (fed_id IS NULL OR component_id IS NULL)
        """))

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE files
        ADD CONSTRAINT files_not_null_check_data
            CHECK (
                (
                    fed_id IS NOT NULL AND
                    component_id IS NOT NULL
                ) OR data IS NOT NULL
            )
        """))
    return True
