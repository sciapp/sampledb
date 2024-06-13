# coding: utf-8
"""
Add migration_indices table to database.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    migration_index_exists = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'migration_index'
    """)).first() is not None
    if migration_index_exists:
        return False

    # Perform migration
    db.session.execute(db.text("""
        CREATE TABLE migration_index (
          migration_index INTEGER
        )
    """))

    # Insert migration index 0
    db.session.execute(db.text("""
        INSERT INTO migration_index
        (migration_index) VALUES (0)
    """))
    return True
