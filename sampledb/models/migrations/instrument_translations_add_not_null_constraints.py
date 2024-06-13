# coding: utf-8
"""
Add missing NOT NULL constraints to foreign key columns in instrument_translations table.
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('instrument_translations', 'instrument_id') and not column_is_nullable('instrument_translations', 'language_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instrument_translations
            ALTER COLUMN instrument_id SET NOT NULL,
            ALTER COLUMN language_id SET NOT NULL
    """))
    return True
