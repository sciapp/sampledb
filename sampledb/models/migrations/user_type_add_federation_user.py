# coding: utf-8
"""
Add FEDERATION_USER enum value to UserType enum.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 78
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    enum_values = db.session.execute(db.text("""
        SELECT unnest(enum_range(NULL::usertype))::text;
    """)).fetchall()
    if ('FEDERATION_USER',) in enum_values:
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
