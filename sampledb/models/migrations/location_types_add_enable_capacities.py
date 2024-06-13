# coding: utf-8
"""
Add enable_capacities to location_types table.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'location_types'
    """)).fetchall()
    if ('enable_capacities',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE location_types
            ADD enable_capacities BOOLEAN NOT NULL DEFAULT false
    """))
    db.session.execute(db.text("""
        ALTER TABLE location_types
            ALTER COLUMN enable_capacities DROP DEFAULT
    """))
    return True
