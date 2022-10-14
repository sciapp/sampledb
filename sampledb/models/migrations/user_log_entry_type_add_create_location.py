# coding: utf-8
"""
Add CREATE_LOCATION enum value to UserLogEntryType enum.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 4
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    enum_values = db.session.execute(db.text("""
        SELECT unnest(enum_range(NULL::userlogentrytype))::text;
    """)).fetchall()
    if ('CREATE_LOCATION',) in enum_values:
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction
    connection = db.engine.connect()
    connection.detach()
    connection.execution_options(autocommit=False)
    connection.execute(db.text("COMMIT"))
    connection.execute(db.text("""
        ALTER TYPE userlogentrytype
        ADD VALUE 'CREATE_LOCATION'
    """))
    connection.close()
    return True
