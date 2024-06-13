# coding: utf-8
"""
Add the show_in_object_filters column to the action_types table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('action_types', 'show_in_object_filters'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD show_in_object_filters BOOLEAN DEFAULT TRUE NOT NULL
    """))
    # Hide non-object-creating action types per default
    db.session.execute(db.text("""
        UPDATE action_types
        SET show_in_object_filters = FALSE
        WHERE disable_create_objects
    """))
    return True
