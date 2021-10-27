# coding: utf-8
"""
Add fed_id and component_id columns to files table.
"""

import os

MIGRATION_INDEX = 86
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'files'
    """).fetchall()
    if ('fed_id',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE files
            ADD fed_id INTEGER,
            ADD component_id INTEGER,
            ADD FOREIGN KEY(component_id) REFERENCES components(id),
            ADD CONSTRAINT files_fed_id_component_id_key UNIQUE(fed_id, object_id, component_id)
    """)
    return True
