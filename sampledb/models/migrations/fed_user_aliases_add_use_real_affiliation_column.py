# coding: utf-8
"""
Add use_real_affiliation column to fed_user_aliases table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('fed_user_aliases', 'use_real_affiliation'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE fed_user_aliases
        ADD use_real_affiliation BOOLEAN NOT NULL DEFAULT(FALSE)
    """))
    return True
