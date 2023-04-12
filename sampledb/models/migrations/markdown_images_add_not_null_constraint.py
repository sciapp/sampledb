# coding: utf-8
"""
Add missing NOT NULL constraint to column in markdown_images table.
"""

import os

import flask_sqlalchemy

from .two_factor_authentication_methods_add_not_null_constraints import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX
from .utils import column_is_nullable

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('markdown_images', 'utc_datetime'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE markdown_images
            ALTER COLUMN utc_datetime SET NOT NULL
    """))
    return True
