# coding: utf-8
"""
Splits action types into action_types and action_type_translations
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..languages import Language


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('action_types', 'name'):
        return False

    # Perform migration
    existing_data = [
        action_data
        for action_data in db.session.execute(db.text("""
            SELECT id, name, description, object_name, object_name_plural, view_text, perform_text
            FROM action_types
        """)).fetchall()
    ]

    db.session.execute(db.text("""
            ALTER TABLE action_types
            DROP COLUMN name,
            DROP COLUMN object_name,
            DROP COLUMN object_name_plural,
            DROP COLUMN view_text,
            DROP COLUMN perform_text
        """))

    performed_migration = False
    for action_type_id, name, description, object_name, object_name_plural, view_text, perform_text in existing_data:
        translation = {
            'action_type_id': action_type_id,
            'language_id': Language.ENGLISH,
            'name': name,
            'description': description,
            'object_name': object_name,
            'object_name_plural': object_name_plural,
            'view_text': view_text,
            'perform_text': perform_text
        }
        # Perform migration
        db.session.execute(db.text("""
                      INSERT INTO action_type_translations (action_type_id, language_id, name, description, object_name, object_name_plural, view_text, perform_text)
                      VALUES (:action_type_id, :language_id, :name, :description, :object_name, :object_name_plural, :view_text, :perform_text)
                  """), params=translation)
        performed_migration = True

    return performed_migration
