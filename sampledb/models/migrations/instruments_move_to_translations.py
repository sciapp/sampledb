# coding: utf-8
"""
Splits action types into action_types and action_type_translations
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..languages import Language


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if not table_has_column('instruments', 'name'):
        return False

    # Perform migration
    existing_data = [
        instrument_data
        for instrument_data in db.session.execute(db.text("""
            SELECT id, name, description, short_description, notes
            FROM instruments
        """)).fetchall()
    ]

    db.session.execute(db.text("""
            ALTER TABLE instruments
            DROP COLUMN name,
            DROP COLUMN description,
            DROP COLUMN short_description,
            DROP COLUMN notes
        """))

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
        db.session.execute(db.text("""
                      INSERT INTO instrument_translations (instrument_id, language_id, name, description, short_description, notes)
                      VALUES (:instrument_id, :language_id, :name, :description, :short_description, :notes)
                  """), params=translation)
        performed_migration = True

    return performed_migration
