# coding: utf-8
"""
Drop the notes column from the instruments table that might have been created by migration 22.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('instruments', 'notes'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
            DROP COLUMN notes
    """))
    return True
