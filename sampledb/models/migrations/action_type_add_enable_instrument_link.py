# coding: utf-8
"""
Add the enable_instrument_link column to the action_types table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('action_types', 'enable_instrument_link'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD enable_instrument_link BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
