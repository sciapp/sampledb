# coding: utf-8
"""
Split show_in_navbar column into show_in_action_navbar and show_in_instrument_navbar in topics table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('topics', 'show_in_navbar'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE topics
        ADD show_in_action_navbar BOOLEAN DEFAULT FALSE NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        ALTER COLUMN show_in_action_navbar DROP DEFAULT
    """))
    db.session.execute(db.text("""
        UPDATE topics
        SET show_in_action_navbar = show_in_navbar
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        ADD show_in_instrument_navbar BOOLEAN DEFAULT FALSE NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        ALTER COLUMN show_in_instrument_navbar DROP DEFAULT
    """))
    db.session.execute(db.text("""
        UPDATE topics
        SET show_in_instrument_navbar = show_in_navbar
    """))
    db.session.execute(db.text("""
        ALTER TABLE topics
        DROP COLUMN show_in_navbar
    """))
    return True
