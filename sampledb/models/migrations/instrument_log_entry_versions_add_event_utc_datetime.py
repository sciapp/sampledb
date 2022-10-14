# coding: utf-8
"""
Add event_utc_datetime to instrument_log_entry_versions table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 48
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'instrument_log_entry_versions'
    """)).fetchall()
    if ('event_utc_datetime',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instrument_log_entry_versions
        ADD event_utc_datetime TIMESTAMP WITHOUT TIME ZONE
    """))
    return True
