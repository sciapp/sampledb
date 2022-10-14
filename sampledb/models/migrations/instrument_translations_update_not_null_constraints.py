# coding: utf-8
"""
Replace NOT NULL constraints by not-empty-check in instrument_translations.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 76
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    constraints = db.session.execute(db.text("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'instrument_translations_not_empty_check'
    """)).fetchall()

    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE instrument_translations
                ADD CONSTRAINT instrument_translations_not_empty_check
                    CHECK (NOT (name IS NULL AND description IS NULL AND notes IS NULL AND short_description IS NULL)),
                ALTER COLUMN name DROP NOT NULL,
                ALTER COLUMN description DROP NOT NULL,
                ALTER COLUMN notes DROP NOT NULL,
                ALTER COLUMN short_description DROP NOT NULL
        """))
    return True
