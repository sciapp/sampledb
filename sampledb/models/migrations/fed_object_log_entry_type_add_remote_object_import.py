# coding: utf-8
"""
Add REMOTE_IMPORT_OBJECT enum value to FedObjectLogEntryType enum.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 137
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    enum_values = db.session.execute(db.text("""
        SELECT unnest(enum_range(NULL::fedobjectlogentrytype))::text;
    """)).fetchall()
    if ('REMOTE_IMPORT_OBJECT',) in enum_values:
        return False

    # Perform migration
    with db.engine.begin() as connection:
        connection.execute(db.text("""
            ALTER TYPE fedobjectlogentrytype
            ADD VALUE 'REMOTE_IMPORT_OBJECT'
        """))
    return True
