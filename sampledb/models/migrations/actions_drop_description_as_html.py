# coding: utf-8
"""
Drop description_as_html column from actions table.
"""

import os

MIGRATION_INDEX = 61
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'actions'
        """).fetchall()
    if ('description_as_html',) not in column_names:
        return False

    # Perform migration
    db.session.execute("""
            ALTER TABLE actions
            DROP COLUMN description_as_html
        """)

    return True
