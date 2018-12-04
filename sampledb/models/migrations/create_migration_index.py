# coding: utf-8
"""
Add migration_indices table to database.
"""

import os

MIGRATION_INDEX = 0
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    migration_index_exists = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'migration_index'
    """).first() is not None
    if migration_index_exists:
        return False

    # Perform migration
    db.session.execute("""
        CREATE TABLE migration_index (
          migration_index INTEGER
        )
    """)

    # Insert migration index 0
    db.session.execute(
        """
        INSERT INTO migration_index
        (migration_index) VALUES (0)
        """
    )
    return True
