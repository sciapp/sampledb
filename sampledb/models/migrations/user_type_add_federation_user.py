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
    with db.engine.begin() as connection:
        connection.execute(db.text("""
            ALTER TYPE usertype
            ADD VALUE 'FEDERATION_USER'
        """))
    return True
