# coding: utf-8
"""
Add last_modified column to fed_user_aliases table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 112
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    user_alias_column_names = db.session.execute(db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'fed_user_aliases'
        """)).fetchall()
    if ('last_modified',) in user_alias_column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE fed_user_aliases
        ADD last_modified TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc');
        ALTER TABLE fed_user_aliases
        ALTER COLUMN last_modified DROP DEFAULT;
    """))
    return True
