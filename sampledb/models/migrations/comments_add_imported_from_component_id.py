"""
Add imported_from_component_id column to comments table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('comments', 'imported_from_component_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE comments
        ADD imported_from_component_id INTEGER,
        ADD FOREIGN KEY (imported_from_component_id) REFERENCES components(id)
    """))
    return True
