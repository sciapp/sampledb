import os

import flask_sqlalchemy

from .fed_identity_add_login_column import MIGRATION_INDEX as PREVIOUS_INDEX
from .utils import table_has_column

MIGRATION_INDEX = PREVIOUS_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column("components", "fed_login_available"):
        return False

    db.session.execute(db.text("""
        ALTER TABLE components
        ADD fed_login_available BOOLEAN NOT NULL
        DEFAULT FALSE;
    """))
    return True
