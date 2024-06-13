# coding: utf-8
"""
Add use_instrument_topics column to actions table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'use_instrument_topics'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD use_instrument_topics BOOLEAN DEFAULT FALSE NOT NULL
    """))
    db.session.execute(db.text("""
        UPDATE actions
        SET use_instrument_topics = TRUE
        WHERE instrument_id IS NOT NULL AND id NOT IN (SELECT action_id FROM action_topics)
    """))
    return True
