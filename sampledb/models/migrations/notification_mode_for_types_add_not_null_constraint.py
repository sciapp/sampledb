# coding: utf-8
"""
Add missing NOT NULL constraints to type column in notification_mode_for_types table.
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('notification_mode_for_types', 'type'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        DELETE FROM notification_mode_for_types
        WHERE type IS NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE notification_mode_for_types
        ALTER COLUMN type SET NOT NULL
    """))
    return True
