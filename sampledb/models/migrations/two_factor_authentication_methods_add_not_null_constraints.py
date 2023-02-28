# coding: utf-8
"""
Add missing NOT NULL constraints to columns in two_factor_authentication_methods table.
"""

import os

import flask_sqlalchemy

from .download_service_job_files_add_not_null_constraints import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX
from .utils import column_is_nullable

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('two_factor_authentication_methods', 'user_id') and not column_is_nullable('two_factor_authentication_methods', 'data'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE two_factor_authentication_methods
            ALTER COLUMN user_id SET NOT NULL,
            ALTER COLUMN data SET NOT NULL
    """))
    return True
