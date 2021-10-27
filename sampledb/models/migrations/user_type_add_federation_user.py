# coding: utf-8
"""
Add FEDERATION_USER enum value to UserType enum.
"""

import os

MIGRATION_INDEX = 78
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    enum_values = db.session.execute("""
        SELECT unnest(enum_range(NULL::usertype))::text;
    """).fetchall()
    if ('FEDERATION_USER',) in enum_values:
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction
    connection = db.engine.connect()
    connection.detach()
    connection.execution_options(autocommit=False)
    connection.execute("COMMIT")
    connection.execute("""
        ALTER TYPE usertype
        ADD VALUE 'FEDERATION_USER'
    """)
    connection.close()
    return True
