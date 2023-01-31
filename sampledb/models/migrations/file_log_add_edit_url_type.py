# coding: utf-8
"""
Add EDIT_URL enum value to FileLogEntryType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_has_value

MIGRATION_INDEX = 100
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if enum_has_value('filelogentrytype', 'EDIT_URL'):
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction (in PostgreSQL 11)
    engine = db.engine.execution_options(autocommit=False)
    with engine.connect() as connection:
        connection.execute(db.text("COMMIT"))
        connection.execute(db.text("""
            ALTER TYPE filelogentrytype
            ADD VALUE 'EDIT_URL'
        """))
    return True
