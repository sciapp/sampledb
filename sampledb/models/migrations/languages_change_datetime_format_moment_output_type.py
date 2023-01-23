# coding: utf-8
"""
Change datetime_format_moment_output column data type to varchar in languages table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 133
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE languages
        ALTER COLUMN datetime_format_moment_output SET DATA TYPE VARCHAR
    """))
    db.session.execute(db.text("""
        ALTER TABLE languages
        ALTER COLUMN datetime_format_moment_output SET DEFAULT 'lll'::VARCHAR
    """))
    return True
