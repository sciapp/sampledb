# coding: utf-8
"""
Drop short_description_as_html column from actions table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 62
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('actions', 'short_description_as_html'):
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE actions
            DROP COLUMN short_description_as_html
        """))

    return True
