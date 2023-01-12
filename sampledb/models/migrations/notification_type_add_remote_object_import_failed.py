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
    with db.engine.begin() as connection:
        connection.execute(db.text("""
            ALTER TYPE notificationtype
            ADD VALUE 'REMOTE_OBJECT_IMPORT_FAILED'
        """))
    return True
