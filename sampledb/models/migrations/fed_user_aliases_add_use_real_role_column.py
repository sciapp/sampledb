# coding: utf-8
"""
Add use_real_role column to fed_user_aliases table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('fed_user_aliases', 'use_real_role'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE fed_user_aliases
        ADD use_real_role BOOLEAN NOT NULL DEFAULT(FALSE)
    """))
    return True
