# coding: utf-8
"""
Add data column to files table.
"""

import os
import sqlalchemy

MIGRATION_INDEX = 8
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'files'
    """).fetchall()
    if ('data',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE files
        ADD data JSON
    """)

    files_to_update = []
    for id, object_id, original_file_name in db.session.execute("""SELECT id, object_id, original_file_name FROM files""").fetchall():
        if original_file_name:
            files_to_update.append((id, object_id, original_file_name))
    for id, object_id, original_file_name in files_to_update:
        db.session.execute(sqlalchemy.text("""
        UPDATE files
        SET data=jsonb_set('{"storage": "local"}'::jsonb, '{original_file_name}', to_json(:original_file_name ::text)::jsonb, true), original_file_name=''
        WHERE id=:id AND object_id=:object_id
        """), params={'id': id, 'object_id': object_id, 'original_file_name': original_file_name})

    db.session.execute("""
        ALTER TABLE files
        DROP COLUMN original_file_name
    """)
    return True
