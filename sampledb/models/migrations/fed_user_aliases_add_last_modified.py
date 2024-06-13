# coding: utf-8
"""
Add last_modified column to fed_user_aliases table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('fed_user_aliases', 'last_modified'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE fed_user_aliases
        ADD last_modified TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc');
        ALTER TABLE fed_user_aliases
        ALTER COLUMN last_modified DROP DEFAULT;
    """))
    return True
