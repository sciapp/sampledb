# coding: utf-8
"""
Drop default value for is_hidden column in locations table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 132
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE locations
            ALTER COLUMN is_hidden DROP DEFAULT
    """))
    return True
