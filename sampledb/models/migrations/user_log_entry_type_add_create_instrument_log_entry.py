# coding: utf-8
"""
Add CREATE_INSTRUMENT_LOG_ENTRY enum value to UserLogEntryType enum.
"""

import os

MIGRATION_INDEX = 18
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    enum_values = db.session.execute("""
        SELECT unnest(enum_range(NULL::userlogentrytype))::text;
    """).fetchall()
    if ('CREATE_INSTRUMENT_LOG_ENTRY',) in enum_values:
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction
    connection = db.engine.connect()
    connection.detach()
    connection.execution_options(autocommit=False)
    connection.execute("COMMIT")
    connection.execute("""
        ALTER TYPE userlogentrytype
        ADD VALUE 'CREATE_INSTRUMENT_LOG_ENTRY'
    """)
    connection.close()
    return True
