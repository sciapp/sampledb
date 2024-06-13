# coding: utf-8
"""
Drop default value for is_hidden column in locations table.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE locations
            ALTER COLUMN is_hidden DROP DEFAULT
    """))
    return True
