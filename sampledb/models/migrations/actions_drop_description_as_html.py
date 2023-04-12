# coding: utf-8
"""
Drop description_as_html column from actions table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 61
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('actions', 'description_as_html'):
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE actions
            DROP COLUMN description_as_html
        """))

    return True
