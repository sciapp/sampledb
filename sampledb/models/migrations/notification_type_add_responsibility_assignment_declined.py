# coding: utf-8
"""
Add RESPONSIBILITY_ASSIGNMENT_DECLINED enum value to NotificationType enum.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 118
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    enum_values = db.session.execute(db.text("""
        SELECT unnest(enum_range(NULL::notificationtype))::text;
    """)).fetchall()
    if ('RESPONSIBILITY_ASSIGNMENT_DECLINED',) in enum_values:
        return False

    # Perform migration
    with db.engine.begin() as connection:
        connection.execute(db.text("""
            ALTER TYPE notificationtype
            ADD VALUE 'RESPONSIBILITY_ASSIGNMENT_DECLINED'
        """))
    return True
