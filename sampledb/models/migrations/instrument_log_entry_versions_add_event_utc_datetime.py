# coding: utf-8
"""
Add event_utc_datetime to instrument_log_entry_versions table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 48
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instrument_log_entry_versions', 'event_utc_datetime'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instrument_log_entry_versions
        ADD event_utc_datetime TIMESTAMP WITHOUT TIME ZONE
    """))
    return True
