"""
Remove unique constraint from lang_code in languages table
"""

import flask_sqlalchemy

from .utils import column_is_unique


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not column_is_unique('languages', 'lang_code'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE languages
        DROP CONSTRAINT languages_lang_code_key
    """))
    return True
