# coding: utf-8
"""
Convert the instrument_log_entries table from containing content to using versioning.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 35
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instrument_log_entries'
    """)).fetchall()
    if ('content',) not in column_names:
        return False

    # Perform migration
    existing_log_entries = db.session.execute(db.text("""
        SELECT id, content, utc_datetime
        FROM instrument_log_entries
    """)).fetchall()
    for log_entry_id, content, utc_datetime in existing_log_entries:
        db.session.execute(db.text("""
        INSERT INTO instrument_log_entry_versions (log_entry_id, version_id, content, utc_datetime)
        VALUES (:log_entry_id, 1, :content, :utc_datetime)
        """), {
            'log_entry_id': log_entry_id,
            'content': content,
            'utc_datetime': utc_datetime
        })
    existing_log_entry_categories = db.session.execute(db.text("""
    SELECT log_entry_id, category_id
    FROM instrument_log_entry_category_associations
    """)).fetchall()
    for log_entry_id, category_id in existing_log_entry_categories:
        db.session.execute(db.text("""
        INSERT INTO instrument_log_entry_version_category_associations (log_entry_id, log_entry_version_id, category_id)
        VALUES (:log_entry_id, 1, :category_id)
        """), {
            'log_entry_id': log_entry_id,
            'category_id': category_id
        })
    db.session.execute(db.text("""
        DROP TABLE instrument_log_entry_category_associations
    """))
    db.session.execute(db.text("""
        ALTER TABLE instrument_log_entries
        DROP content
    """))
    db.session.execute(db.text("""
        ALTER TABLE instrument_log_entries
        DROP utc_datetime
    """))
    db.session.execute(db.text("""
        ALTER TABLE instrument_log_file_attachments
        ADD is_hidden BOOLEAN DEFAULT FALSE NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE instrument_log_object_attachments
        ADD is_hidden BOOLEAN DEFAULT FALSE NOT NULL
    """))
    return True
