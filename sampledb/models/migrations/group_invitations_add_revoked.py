# coding: utf-8
"""
Add revoked columns to group_invitations table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column
from .files_add_preview_image import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('group_invitations', 'revoked'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE group_invitations
        ADD revoked BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
