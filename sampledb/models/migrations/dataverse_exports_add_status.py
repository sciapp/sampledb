"""
Add the status column to the dataverse_exports table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 125
MIGRATION_NAME, _ = os.path.split(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'dataverse_exports'
    """)).fetchall()
    if ('status', ) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        CREATE TYPE dataverse_export_status
        AS ENUM ('TASK_CREATED', 'EXPORT_FINISHED')
    """))
    db.session.execute(db.text("""
        ALTER TABLE dataverse_exports
        ALTER COLUMN dataverse_url DROP NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE dataverse_exports
        ADD COLUMN status dataverse_export_status NOT NULL
    """))

    return True
