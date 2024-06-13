# coding utf-8
"""
Add the order_index column to the action_types table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('action_types', 'order_index'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD order_index INTEGER NULL
    """))
    return True
