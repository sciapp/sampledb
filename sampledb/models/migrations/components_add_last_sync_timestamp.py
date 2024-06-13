# coding: utf-8
"""
Add last_sync_timestamp column to components table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('components', 'last_sync_timestamp'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE components
            ADD last_sync_timestamp TIMESTAMP WITHOUT TIME ZONE
    """))
    return True
