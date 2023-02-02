# coding: utf-8
"""
Add REMOTE_OBJECT_IMPORT_FAILED enum value to NotificationType enum.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 139
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    enum_values = db.session.execute(db.text("""
        SELECT unnest(enum_range(NULL::notificationtype))::text;
    """)).fetchall()
    if ('REMOTE_OBJECT_IMPORT_FAILED',) in enum_values:
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction (in PostgreSQL 11)
    engine = db.engine.execution_options(autocommit=False)
    with engine.connect() as connection:
        connection.execute(db.text("COMMIT"))
        connection.execute(db.text("""
            ALTER TYPE notificationtype
            ADD VALUE 'REMOTE_OBJECT_IMPORT_FAILED'
        """))
    return True
