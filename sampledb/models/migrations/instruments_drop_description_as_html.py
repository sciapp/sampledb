# coding: utf-8
"""
Drop description_as_html column from instruments table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('instruments', 'description_as_html'):
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE instruments
            DROP COLUMN description_as_html
        """))

    return True
