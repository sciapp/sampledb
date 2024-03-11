import os

import flask_sqlalchemy

from .object_log_add_is_imported import MIGRATION_INDEX as PREVIOUS_INDEX
from .utils import table_has_column

MIGRATION_INDEX = PREVIOUS_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column("fed_identities", "login"):
        return False

    db.session.execute(db.text("""
        ALTER TABLE fed_identities
        ADD login BOOLEAN NOT NULL
        DEFAULT FALSE;
    """))
    return True
