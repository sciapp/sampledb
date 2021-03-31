# coding: utf-8
"""
Splits action types into action_types and action_type_translations
"""

import os

from ..languages import Language

MIGRATION_INDEX = 51
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'action_types'
        """).fetchall()
    if ('name', ) not in column_names:
        return False

    # Perform migration
    existing_data = [
        action_data
        for action_data in db.session.execute("""
            SELECT id, name, description, object_name, object_name_plural, view_text, perform_text
            FROM action_types
        """).fetchall()
    ]

    db.session.execute("""
            ALTER TABLE action_types
            DROP COLUMN name,
            DROP COLUMN object_name,
            DROP COLUMN object_name_plural,
            DROP COLUMN view_text,
            DROP COLUMN perform_text
        """)

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
        db.session.execute("""
                      INSERT INTO action_type_translations (action_type_id, language_id, name, description, object_name, object_name_plural, view_text, perform_text)
                      VALUES (:action_type_id, :language_id, :name, :description, :object_name, :object_name_plural, :view_text, :perform_text)
                  """, params=translation)
        performed_migration = True

    return performed_migration
