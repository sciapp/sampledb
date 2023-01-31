"""
Add the result and expiration date column to the background_tasks table.
"""

import os

import flask_sqlalchemy

from .utils import table_has_column

MIGRATION_INDEX = 124
MIGRATION_NAME, _ = os.path.split(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('background_tasks', 'result'):
        return False

    # Perform migration
    db.session.execute(db.text(
        """
        ALTER TABLE background_tasks
        ADD expiration_date TIMESTAMP NULL,
        ADD result JSON NULL
        """
    ))
    return True
