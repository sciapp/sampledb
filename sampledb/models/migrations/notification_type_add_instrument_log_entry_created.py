# coding: utf-8
"""
Add INSTRUMENT_LOG_ENTRY_CREATED enum value to NotificationType enum.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 19
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    enum_values = db.session.execute(db.text("""
        SELECT unnest(enum_range(NULL::notificationtype))::text;
    """)).fetchall()
    if ('INSTRUMENT_LOG_ENTRY_CREATED',) in enum_values:
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction
    connection = db.engine.connect()
    connection.detach()
    connection.execution_options(autocommit=False)
    connection.execute(db.text("COMMIT"))
    connection.execute(db.text("""
        ALTER TYPE notificationtype
        ADD VALUE 'INSTRUMENT_LOG_ENTRY_CREATED'
    """))
    connection.close()
    return True
