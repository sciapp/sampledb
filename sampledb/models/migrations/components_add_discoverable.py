# coding: utf-8
"""
Add discoverable column to components table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('components', 'discoverable'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE components
            ADD discoverable BOOLEAN NOT NULL DEFAULT true
    """))
    return True
