# coding: utf-8
"""
Remove NOT NULL constraints for utc_datetime column as intended by migration 85.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ALTER COLUMN utc_datetime DROP NOT NULL
    """))
    return True
