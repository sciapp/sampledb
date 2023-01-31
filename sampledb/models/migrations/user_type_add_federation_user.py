# coding: utf-8
"""
Add FEDERATION_USER enum value to UserType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_has_value

MIGRATION_INDEX = 78
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if enum_has_value('usertype', 'FEDERATION_USER'):
        return False

    # Perform migration
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction (in PostgreSQL 11)
    engine = db.engine.execution_options(autocommit=False)
    with engine.connect() as connection:
        connection.execute(db.text("COMMIT"))
        connection.execute(db.text("""
            ALTER TYPE usertype
            ADD VALUE 'FEDERATION_USER'
        """))
    return True
