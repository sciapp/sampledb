# coding: utf-8
"""
Replace NOT NULL constraints by not-empty-check in action_translations.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 91
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    constraints = db.session.execute(db.text("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'action_translations_not_empty_check'
    """)).fetchall()

    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE action_translations
                ADD CONSTRAINT action_translations_not_empty_check
                    CHECK (NOT (name IS NULL AND description IS NULL AND short_description IS NULL)),
                ALTER COLUMN name DROP NOT NULL,
                ALTER COLUMN description DROP NOT NULL,
                ALTER COLUMN short_description DROP NOT NULL
        """))
    return True
