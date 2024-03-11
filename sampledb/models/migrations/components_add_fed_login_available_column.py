"""
Add fed_login_available column to components table
"""
import flask_sqlalchemy

from .utils import table_has_column


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
