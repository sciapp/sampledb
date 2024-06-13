# coding: utf-8
"""
Add the disable_create_objects column to the actions table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'disable_create_objects'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD disable_create_objects boolean NOT NULL DEFAULT(FALSE)
    """))
    return True
