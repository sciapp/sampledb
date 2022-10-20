# coding: utf-8
"""
Add EDIT_URL enum value to FileLogEntryType enum.
"""

import os

MIGRATION_INDEX = 100
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    enum_values = db.session.execute(db.text("""
        SELECT unnest(enum_range(NULL::filelogentrytype))::text;
    """)).fetchall()
    if ('EDIT_URL',) in enum_values:
        return False

    # Perform migration
    with db.engine.begin() as connection:
        connection.execute(db.text("""
            ALTER TYPE filelogentrytype
            ADD VALUE 'EDIT_URL'
        """))
    return True
