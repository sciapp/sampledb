# coding: utf-8
"""
Add the signed_by column to the eln_imports table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('eln_imports', 'signed_by'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE eln_imports
        ADD signed_by VARCHAR
    """))
    return True
