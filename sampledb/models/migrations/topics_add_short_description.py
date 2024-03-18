# coding: utf-8
"""
Add short_description column to topics table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column
from .notification_type_add_automatic_user_federation import MIGRATION_INDEX as PREVIOUS_INDEX

MIGRATION_INDEX = PREVIOUS_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('topics', 'short_description'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE topics
        ADD short_description JSON NOT NULL DEFAULT '{}'::json
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        ALTER COLUMN short_description DROP DEFAULT
    """))
    return True
