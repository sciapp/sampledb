# coding: utf-8
"""
Add missing NOT NULL constraints to foreign key columns in action_type_translations table.
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('action_type_translations', 'action_type_id') and not column_is_nullable('action_type_translations', 'language_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_type_translations
            ALTER COLUMN action_type_id SET NOT NULL,
            ALTER COLUMN language_id SET NOT NULL
    """))
    return True
