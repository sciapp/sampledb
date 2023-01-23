"""
Add the result and expiration date column to the background_tasks table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 124
MIGRATION_NAME, _ = os.path.split(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'background_tasks'
        """)).fetchall()
    if ('result', ) in column_names:
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
