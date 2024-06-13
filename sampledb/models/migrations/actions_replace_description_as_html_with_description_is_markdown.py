# coding: utf-8
"""
Replace description_as_html column with description_is_markdown in actions table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'description_is_markdown'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD description_is_markdown BOOLEAN NOT NULL DEFAULT FALSE
    """))
    db.session.execute(db.text("""
        UPDATE actions
        SET description_is_markdown = TRUE
        WHERE description_as_html IS NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE actions
        DROP description_as_html
    """))
    return True
