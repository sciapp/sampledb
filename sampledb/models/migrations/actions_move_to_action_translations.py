# coding: utf-8
"""
Splits actions into action and action_translations
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..languages import Language


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('actions', 'name'):
        return False

    # Perform migration
    existing_data = [
        action_data
        for action_data in db.session.execute(db.text("""
            SELECT id, name, description, short_description
            FROM actions
        """)).fetchall()
    ]

    db.session.execute(db.text("""
            ALTER TABLE actions
            DROP COLUMN name,
            DROP COLUMN description,
            DROP COLUMN short_description
        """))

    for action_id, name, description, short_description in existing_data:
        # Perform migration
        translation = {
            'action_id': action_id,
            'language_id': Language.ENGLISH,
            'name': name,
            'description': description,
            'short_description': short_description,
        }
        db.session.execute(db.text("""
                      INSERT INTO action_translations (action_id, language_id, name, description, short_description)
                      VALUES (:action_id, :language_id, :name, :description, :short_description)
                  """), params=translation)

    return True
