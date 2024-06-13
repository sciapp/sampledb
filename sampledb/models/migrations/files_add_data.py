# coding: utf-8
"""
Add data column to files table.
"""

import flask_sqlalchemy
import sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('files', 'data'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE files
        ADD data JSON
    """))

    files_to_update = []
    for id, object_id, original_file_name in db.session.execute(db.text("""SELECT id, object_id, original_file_name FROM files""")).fetchall():
        if original_file_name:
            files_to_update.append((id, object_id, original_file_name))
    for id, object_id, original_file_name in files_to_update:
        db.session.execute(sqlalchemy.text(db.text("""
        UPDATE files
        SET data=jsonb_set('{"storage": "local"}'::jsonb, '{original_file_name}', to_json(:original_file_name ::text)::jsonb, true), original_file_name=''
        WHERE id=:id AND object_id=:object_id
        """)), params={'id': id, 'object_id': object_id, 'original_file_name': original_file_name})

    db.session.execute(db.text("""
        ALTER TABLE files
        DROP COLUMN original_file_name
    """))
    return True
