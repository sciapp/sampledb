"""
Add the status column to the dataverse_exports table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('dataverse_exports', 'status'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE dataverse_exports
        ALTER COLUMN dataverse_url DROP NOT NULL
    """))
    db.session.execute(db.text("""
        ALTER TABLE dataverse_exports
        ADD COLUMN status dataverseexportstatus NULL
    """))
    db.session.execute(db.text("""
        UPDATE dataverse_exports
        SET status = 'EXPORT_FINISHED'::dataverseexportstatus
    """))
    db.session.execute(db.text("""
        ALTER TABLE dataverse_exports
        ALTER COLUMN status SET NOT NULL
    """))
    return True
