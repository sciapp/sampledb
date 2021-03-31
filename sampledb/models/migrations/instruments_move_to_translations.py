# coding: utf-8
"""
Splits action types into action_types and action_type_translations
"""

import os

from ..languages import Language

MIGRATION_INDEX = 53
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'instruments'
        """).fetchall()
    if ('name',) not in column_names:
        return False

    # Perform migration
    existing_data = [
        instrument_data
        for instrument_data in db.session.execute("""
            SELECT id, name, description, short_description, notes
            FROM instruments
        """).fetchall()
    ]

    db.session.execute("""
            ALTER TABLE instruments
            DROP COLUMN name,
            DROP COLUMN description,
            DROP COLUMN short_description,
            DROP COLUMN notes
        """)

    performed_migration = False
    for instrument_id, name, description, short_description, notes in existing_data:
        translation = {
            'instrument_id': instrument_id,
            'language_id': Language.ENGLISH,
            'name': name,
            'description': description,
            'short_description': short_description,
            'notes': notes
        }
        # Perform migration
        db.session.execute("""
                      INSERT INTO instrument_translations (instrument_id, language_id, name, description, short_description, notes)
                      VALUES (:instrument_id, :language_id, :name, :description, :short_description, :notes)
                  """, params=translation)
        performed_migration = True

    return performed_migration
