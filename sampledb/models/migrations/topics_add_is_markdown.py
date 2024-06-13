# coding: utf-8
"""
Add description_is_markdown and short_description_is_markdown columns to topics table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    has_description_is_markdown = table_has_column('topics', 'description_is_markdown')
    has_short_description_is_markdown = table_has_column('topics', 'short_description_is_markdown')
    # Skip migration by condition
    if has_description_is_markdown and has_short_description_is_markdown:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE topics
        ADD description_is_markdown BOOLEAN DEFAULT FALSE NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        ALTER COLUMN description_is_markdown DROP DEFAULT
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        ADD short_description_is_markdown BOOLEAN DEFAULT FALSE NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        ALTER COLUMN short_description_is_markdown DROP DEFAULT
    """))
    return True
