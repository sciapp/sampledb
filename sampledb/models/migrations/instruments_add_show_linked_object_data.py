# coding: utf-8
"""
Add the show_linked_object_data column to the instruments table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'show_linked_object_data'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD show_linked_object_data BOOLEAN DEFAULT TRUE NOT NULL
    """))
    return True
