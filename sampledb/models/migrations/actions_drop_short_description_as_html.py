# coding: utf-8
"""
Drop short_description_as_html column from actions table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 62
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'actions'
        """)).fetchall()
    if ('short_description_as_html',) not in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE actions
            DROP COLUMN short_description_as_html
        """))

    return True
