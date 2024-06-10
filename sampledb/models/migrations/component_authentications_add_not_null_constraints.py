# coding: utf-8
"""
Add missing NOT NULL constraints to columns in component_authentications table.
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('component_authentications', 'component_id') and not column_is_nullable('component_authentications', 'login') and not column_is_nullable('component_authentications', 'type'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE component_authentications
            ALTER COLUMN component_id SET NOT NULL,
            ALTER COLUMN login SET NOT NULL,
            ALTER COLUMN type SET NOT NULL
    """))
    return True
