# coding: utf-8
"""
Add use_real_affiliation column to fed_user_aliases table.
"""

import os

MIGRATION_INDEX = 107
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    user_alias_column_names = db.session.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'fed_user_aliases'
        """).fetchall()
    if ('use_real_affiliation',) in user_alias_column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE fed_user_aliases
        ADD use_real_affiliation BOOLEAN NOT NULL DEFAULT(FALSE)
    """)
    return True
