# coding: utf-8
"""
Create default action type translations.
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..actions import ActionType
from ..languages import Language


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('action_types', 'name'):
        return False

    default_action_type_translation = [
        {
            'action_type_id': ActionType.SAMPLE_CREATION,
            'language_id': Language.ENGLISH,
            'name': 'Sample Creation',
            'description': 'These Actions represent processes which create a sample.',
            'object_name': 'Sample',
            'object_name_plural': 'Samples',
            'view_text': 'View Samples',
            'perform_text': 'Create Sample',
        },
        {
            'action_type_id': ActionType.MEASUREMENT,
            'language_id': Language.ENGLISH,
            'name': 'Measurement',
            'description': 'These Actions represent processes which perform a measurement.',
            'object_name': 'Measurement',
            'object_name_plural': 'Measurements',
            'view_text': 'View Measurements',
            'perform_text': 'Perform Measurement',
        },
        {
            'action_type_id': ActionType.SIMULATION,
            'language_id': Language.ENGLISH,
            'name': 'Simulation',
            'description': 'These Actions represent processes which run a simulation.',
            'object_name': 'Simulation',
            'object_name_plural': 'Simulations',
            'view_text': 'View Simulations',
            'perform_text': 'Run Simulation',
        },
        {
            'action_type_id': ActionType.SAMPLE_CREATION,
            'language_id': Language.GERMAN,
            'name': 'Probenerstellung',
            'description': 'Diese Aktionen repräsentieren Prozesse, die Proben erstellen.',
            'object_name': 'Probe',
            'object_name_plural': 'Proben',
            'view_text': 'Proben anzeigen',
            'perform_text': 'Probe erstellen',
        },
        {
            'action_type_id': ActionType.MEASUREMENT,
            'language_id': Language.GERMAN,
            'name': 'Messung',
            'description': 'Diese Aktionen repräsentieren Prozesse, die Messungen durchführen.',
            'object_name': 'Messung',
            'object_name_plural': 'Messungen',
            'view_text': 'Messungen anzeigen',
            'perform_text': 'Messung durchführen',
        },
        {
            'action_type_id': ActionType.SIMULATION,
            'language_id': Language.GERMAN,
            'name': 'Simulation',
            'description': 'Diese Aktionen repräsentieren Prozesse, die Simulationen durchführen.',
            'object_name': 'Simulation',
            'object_name_plural': 'Simulationen',
            'view_text': 'Simulationen anzeigen',
            'perform_text': 'Simulation durchführen',
        }
    ]
    existing_translation_action_type_and_language_ids = [
        (action_type_id, language_id)
        for action_type_id, language_id in db.session.execute(db.text("""
            SELECT action_type_id, language_id
            FROM action_type_translations
        """)).fetchall()
    ]
    performed_migration = False
    for action_type_translation in default_action_type_translation:
        # Skip migration by condition
        if (action_type_translation['action_type_id'], action_type_translation['language_id']) in existing_translation_action_type_and_language_ids:
            continue

        # Perform migration
        db.session.execute(db.text("""
            INSERT INTO action_type_translations (action_type_id, language_id, name, description, object_name, object_name_plural, view_text, perform_text)
            VALUES (:action_type_id, :language_id,:name, :description, :object_name, :object_name_plural, :view_text, :perform_text)
        """), params=action_type_translation)
        performed_migration = True
    return performed_migration
