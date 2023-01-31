# coding: utf-8
"""
Add REMOTE_IMPORT_OBJECT enum value to FedObjectLogEntryType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_has_value

MIGRATION_INDEX = 137
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if enum_has_value('fedobjectlogentrytype', 'REMOTE_IMPORT_OBJECT'):
        return False

    # Perform migration
    with db.engine.begin() as connection:
        connection.execute(db.text("""
            ALTER TYPE fedobjectlogentrytype
            ADD VALUE 'REMOTE_IMPORT_OBJECT'
        """))
    return True
