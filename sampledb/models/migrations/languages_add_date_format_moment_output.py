# coding: utf-8
"""
Add date_format_moment_output column to languages table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('languages', 'date_format_moment_output'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE languages
        ADD date_format_moment_output character varying NOT NULL DEFAULT 'll'
    """))
    db.session.execute(db.text("""
        UPDATE languages
        SET date_format_moment_output = 'MMM D, YYYY'
        WHERE id = -99
    """))
    db.session.execute(db.text("""
        UPDATE languages
        SET date_format_moment_output = 'DD.MM.YYYY'
        WHERE id = -98
    """))
    return True
