# coding: utf-8
"""
Add INSTRUMENT_LOG_ENTRY_EDITED enum value to NotificationType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_has_value

MIGRATION_INDEX = 34
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if enum_has_value('notificationtype', 'INSTRUMENT_LOG_ENTRY_EDITED'):
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction
    connection = db.engine.connect()
    connection.detach()
    connection.execution_options(autocommit=False)
    connection.execute(db.text("COMMIT"))
    connection.execute(db.text("""
        ALTER TYPE notificationtype
        ADD VALUE 'INSTRUMENT_LOG_ENTRY_EDITED'
    """))
    connection.close()
    return True
