import flask_sqlalchemy

from .utils import table_has_column


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
