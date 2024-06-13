# coding: utf-8
"""
Add create_log_entry_default column to instruments table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'create_log_entry_default'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
        ADD create_log_entry_default BOOLEAN NOT NULL DEFAULT FALSE
    """))
    return True
