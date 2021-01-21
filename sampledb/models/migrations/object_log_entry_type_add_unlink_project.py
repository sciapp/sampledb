# coding: utf-8
"""
Add UNLINK_PROJECT enum value to ObjectLogEntryType enum.
"""

import os

MIGRATION_INDEX = 45
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    enum_values = db.session.execute("""
        SELECT unnest(enum_range(NULL::objectlogentrytype))::text;
    """).fetchall()
    if ('UNLINK_PROJECT',) in enum_values:
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction
    connection = db.engine.connect()
    connection.detach()
    connection.execution_options(autocommit=False)
    connection.execute("COMMIT")
    connection.execute("""
        ALTER TYPE objectlogentrytype
        ADD VALUE 'UNLINK_PROJECT'
    """)
    connection.close()
    return True
