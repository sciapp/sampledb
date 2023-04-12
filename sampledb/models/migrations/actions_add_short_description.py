# coding: utf-8
"""
Add short_description and short_description_is_markdown columns to actions table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 41
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'short_description'):
        return False
    if not table_has_column('actions', 'name'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD short_description TEXT NOT NULL DEFAULT ''
    """))
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD short_description_is_markdown BOOLEAN NOT NULL DEFAULT FALSE
    """))
    db.session.execute(db.text("""
        UPDATE actions
        SET short_description = description, short_description_is_markdown=description_is_markdown
    """))
    return True
