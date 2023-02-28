# coding: utf-8
"""
Add missing NOT NULL constraints to columns in languages table.
"""

import os

import flask_sqlalchemy

from .markdown_images_add_not_null_constraint import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX
from .utils import column_is_nullable

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('languages', 'datetime_format_datetime') and not column_is_nullable('languages', 'datetime_format_moment'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE languages
            ALTER COLUMN datetime_format_datetime SET NOT NULL,
            ALTER COLUMN datetime_format_moment SET NOT NULL
    """))
    return True
