# coding: utf-8
"""
Add REFERENCED_BY_OBJECT_METADATA enum value to NotificationType enum.
"""

import os

MIGRATION_INDEX = 29
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    enum_values = db.session.execute("""
        SELECT unnest(enum_range(NULL::notificationtype))::text;
    """).fetchall()
    if ('REFERENCED_BY_OBJECT_METADATA',) in enum_values:
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction
    connection = db.engine.connect()
    connection.detach()
    connection.execution_options(autocommit=False)
    connection.execute("COMMIT")
    connection.execute("""
        ALTER TYPE notificationtype
        ADD VALUE 'REFERENCED_BY_OBJECT_METADATA'
    """)
    connection.close()
    return True
