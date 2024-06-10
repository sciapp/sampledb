# coding: utf-8
"""
Create default action types.
"""

import typing

import flask_sqlalchemy

from .utils import table_has_column
from ..actions import ActionType


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    pre_translation = table_has_column('action_types', 'name')

    existing_action_type_ids = [
        action_type[0]
        for action_type in db.session.execute(db.text("""
                    SELECT id
                    FROM action_types;
                """)).fetchall()
    ]

    # checks if translatable columns still exist in action_types
    if pre_translation:
        default_action_types = [
            {
                'id': ActionType.SAMPLE_CREATION,
                'name': 'Sample Creation',
                'description': 'These Actions represent processes which create a sample.',
                'object_name': 'Sample',
                'object_name_plural': 'Samples',
                'view_text': 'View Samples',
                'perform_text': 'Create Sample',
                'admin_only': False,
                'show_on_frontpage': True,
                'show_in_navbar': True,
                'enable_labels': True,
                'enable_files': True,
                'enable_locations': True,
                'enable_publications': True,
                'enable_comments': True,
                'enable_activity_log': True,
                'enable_related_objects': True
            },
            {
                'id': ActionType.MEASUREMENT,
                'name': 'Measurement',
                'description': 'These Actions represent processes which perform a measurement.',
                'object_name': 'Measurement',
                'object_name_plural': 'Measurements',
                'view_text': 'View Measurements',
                'perform_text': 'Perform Measurement',
                'admin_only': False,
                'show_on_frontpage': True,
                'show_in_navbar': True,
                'enable_labels': False,
                'enable_files': True,
                'enable_locations': True,
                'enable_publications': True,
                'enable_comments': True,
                'enable_activity_log': True,
                'enable_related_objects': True
            },
            {
                'id': ActionType.SIMULATION,
                'name': 'Simulation',
                'description': 'These Actions represent processes which run a simulation.',
                'object_name': 'Simulation',
                'object_name_plural': 'Simulations',
                'view_text': 'View Simulations',
                'perform_text': 'Run Simulation',
                'admin_only': False,
                'show_on_frontpage': True,
                'show_in_navbar': True,
                'enable_labels': False,
                'enable_files': True,
                'enable_locations': True,
                'enable_publications': True,
                'enable_comments': True,
                'enable_activity_log': True,
                'enable_related_objects': True
            }
        ]

        performed_migration = False
        for action_type in default_action_types:
            # Skip migration by condition
            if action_type['id'] in existing_action_type_ids:
                continue

            # Perform migration
            db.session.execute(db.text("""
                INSERT INTO action_types (id, name, description, object_name, object_name_plural, view_text, perform_text, admin_only, show_on_frontpage, show_in_navbar, enable_labels, enable_files, enable_locations, enable_publications, enable_comments, enable_activity_log, enable_related_objects)
                VALUES (:id, :name, :description, :object_name, :object_name_plural, :view_text, :perform_text, :admin_only, :show_on_frontpage, :show_in_navbar, :enable_labels, :enable_files, :enable_locations, :enable_publications, :enable_comments, :enable_activity_log, :enable_related_objects)
            """), params=action_type)
            performed_migration = True

        return performed_migration
    else:
        default_action_types = [
            {
                'id': ActionType.SAMPLE_CREATION,
                'admin_only': False,
                'show_on_frontpage': True,
                'show_in_navbar': True,
                'enable_labels': True,
                'enable_files': True,
                'enable_locations': True,
                'enable_publications': True,
                'enable_comments': True,
                'enable_activity_log': True,
                'enable_related_objects': True,
                'enable_project_link': False
            },
            {
                'id': ActionType.MEASUREMENT,
                'admin_only': False,
                'show_on_frontpage': True,
                'show_in_navbar': True,
                'enable_labels': False,
                'enable_files': True,
                'enable_locations': True,
                'enable_publications': True,
                'enable_comments': True,
                'enable_activity_log': True,
                'enable_related_objects': True,
                'enable_project_link': False
            },
            {
                'id': ActionType.SIMULATION,
                'admin_only': False,
                'show_on_frontpage': True,
                'show_in_navbar': True,
                'enable_labels': False,
                'enable_files': True,
                'enable_locations': True,
                'enable_publications': True,
                'enable_comments': True,
                'enable_activity_log': True,
                'enable_related_objects': True,
                'enable_project_link': False
            }
        ]

        scicat_export_types = {
            ActionType.SAMPLE_CREATION: 'SAMPLE',
            ActionType.MEASUREMENT: 'RAW_DATASET',
            ActionType.SIMULATION: 'RAW_DATASET'
        }

        performed_migration = False

        existing_action_type_ids = [
            action_type[0]
            for action_type in db.session.execute(db.text("""
                             SELECT id
                             FROM action_types
                         """)).fetchall()
        ]

        for action_type in default_action_types:
            action_type_id: int = typing.cast(int, action_type['id'])

            # Skip migration by condition
            if action_type_id in existing_action_type_ids:
                continue

            # Perform migration
            db.session.execute(db.text("""
                          INSERT INTO action_types (id, admin_only, show_on_frontpage, show_in_navbar, enable_labels, enable_files, enable_locations, enable_publications, enable_comments, enable_activity_log, enable_related_objects)
                          VALUES (:id, :admin_only, :show_on_frontpage, :show_in_navbar, :enable_labels, :enable_files, :enable_locations, :enable_publications, :enable_comments, :enable_activity_log, :enable_related_objects)
                      """), params=action_type)
            performed_migration = True

            if action_type_id in scicat_export_types:
                db.session.execute(db.text("""
                    UPDATE action_types
                    SET scicat_export_type = :export_type
                    WHERE id = :id
                """), {
                    "id": action_type_id,
                    "export_type": scicat_export_types[action_type_id]
                })

        return performed_migration
