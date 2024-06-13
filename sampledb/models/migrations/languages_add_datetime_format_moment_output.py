# coding: utf-8
"""
Add datetime_format_moment_output column to languages table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('languages', 'datetime_format_moment_output'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE languages
        ADD datetime_format_moment_output TEXT NOT NULL DEFAULT 'lll'
    """))
    db.session.execute(db.text("""
        UPDATE languages
        SET datetime_format_moment_output = 'MMM D, YYYY, h:mm:ss A'
        WHERE id = -99
    """))
    db.session.execute(db.text("""
        UPDATE languages
        SET datetime_format_moment_output = 'DD.MM.YYYY HH:mm:ss'
        WHERE id = -98
    """))
    return True
