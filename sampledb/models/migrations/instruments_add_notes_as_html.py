# coding: utf-8
"""
Add notes_as_html column to instruments table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'notes_as_html'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD notes_as_html TEXT NULL
    """))
    return True
