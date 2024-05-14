# coding: utf-8
"""
Add preview_image_binary_data and preview_image_mime_type columns to files table.
"""

import os

import flask_sqlalchemy

from .languages_add_date_format_moment_output import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX
from .utils import table_has_column

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('files', 'preview_image_binary_data'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE files
        ADD preview_image_binary_data BYTEA NULL,
        ADD preview_image_mime_type VARCHAR NULL
    """))
    return True
