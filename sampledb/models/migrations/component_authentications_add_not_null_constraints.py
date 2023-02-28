# coding: utf-8
"""
Add missing NOT NULL constraints to columns in component_authentications table.
"""

import os

import flask_sqlalchemy

from .authentications_add_not_null_constraints import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX
from .utils import column_is_nullable

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


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
