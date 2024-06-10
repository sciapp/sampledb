# coding: utf-8
"""
Add missing NOT NULL constraints to columns in download_service_job_files table.
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_nullable('download_service_job_files', 'creation') and not column_is_nullable('download_service_job_files', 'expiration'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE download_service_job_files
            ALTER COLUMN creation SET NOT NULL,
            ALTER COLUMN expiration SET NOT NULL
    """))
    return True
