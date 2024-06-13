# coding: utf-8
"""
Add missing NOT NULL constraints to columns in authentications table.
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('authentications', 'user_id') and not column_is_nullable('authentications', 'login') and not column_is_nullable('authentications', 'type'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE authentications
            ALTER COLUMN user_id SET NOT NULL,
            ALTER COLUMN login SET NOT NULL,
            ALTER COLUMN type SET NOT NULL
    """))
    return True
