# coding: utf-8
"""
Splits actions into action and action_translations
"""

import os

from ..languages import Language

MIGRATION_INDEX = 50
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'actions'
        """).fetchall()
    if ('name',) not in column_names:
        return False

    # Perform migration
    existing_data = [
        action_data
        for action_data in db.session.execute("""
            SELECT id, name, description, short_description
            FROM actions
        """).fetchall()
    ]

    db.session.execute("""
            ALTER TABLE actions
            DROP COLUMN name,
            DROP COLUMN description,
            DROP COLUMN short_description
        """)

    for action_id, name, description, short_description in existing_data:
        # Perform migration
        translation = {
            'action_id': action_id,
            'language_id': Language.ENGLISH,
            'name': name,
            'description': description,
            'short_description': short_description,
        }
        db.session.execute("""
                      INSERT INTO action_translations (action_id, language_id, name, description, short_description)
                      VALUES (:action_id, :language_id, :name, :description, :short_description)
                  """, params=translation)

    return True
