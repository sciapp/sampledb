# coding: utf-8
"""
Add missing NOT NULL constraints to columns in two_factor_authentication_methods table.
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('two_factor_authentication_methods', 'user_id') and not column_is_nullable('two_factor_authentication_methods', 'data'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE two_factor_authentication_methods
            ALTER COLUMN user_id SET NOT NULL,
            ALTER COLUMN data SET NOT NULL
    """))
    return True
