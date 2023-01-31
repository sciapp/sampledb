# coding: utf-8
"""
Add CREATE_INSTRUMENT_LOG_ENTRY enum value to UserLogEntryType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_has_value

MIGRATION_INDEX = 18
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if enum_has_value('userlogentrytype', 'CREATE_INSTRUMENT_LOG_ENTRY'):
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction
    connection = db.engine.connect()
    connection.detach()
    connection.execution_options(autocommit=False)
    connection.execute(db.text("COMMIT"))
    connection.execute(db.text("""
        ALTER TYPE userlogentrytype
        ADD VALUE 'CREATE_INSTRUMENT_LOG_ENTRY'
    """))
    connection.close()
    return True
