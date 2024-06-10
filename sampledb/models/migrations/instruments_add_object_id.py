# coding: utf-8
"""
Add object_id column to instruments table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('instruments', 'object_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE instruments
            ADD object_id INTEGER,
            ADD FOREIGN KEY(object_id) REFERENCES objects_current(object_id)
    """))
    return True
