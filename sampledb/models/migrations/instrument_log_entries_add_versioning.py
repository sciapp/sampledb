# coding: utf-8
"""
Convert the instrument_log_entries table from containing content to using versioning.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('instrument_log_entries', 'content'):
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
