# coding: utf-8
"""
Create default action types.
"""

import os

from ..actions import ActionType

MIGRATION_INDEX = 30
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    action_type_columns = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'action_types';
        """).fetchall()
    pre_translation = ('name',) in action_type_columns

    existing_action_type_ids = [
        action_type[0]
        for action_type in db.session.execute("""
                    SELECT id
                    FROM action_types;
                """).fetchall()
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
            db.session.execute("""
                INSERT INTO action_types (id, name, description, object_name, object_name_plural, view_text, perform_text, admin_only, show_on_frontpage, show_in_navbar, enable_labels, enable_files, enable_locations, enable_publications, enable_comments, enable_activity_log, enable_related_objects)
                VALUES (:id, :name, :description, :object_name, :object_name_plural, :view_text, :perform_text, :admin_only, :show_on_frontpage, :show_in_navbar, :enable_labels, :enable_files, :enable_locations, :enable_publications, :enable_comments, :enable_activity_log, :enable_related_objects)
            """, params=action_type)
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

        performed_migration = False

        existing_action_type_ids = [
            action_type[0]
            for action_type in db.session.execute("""
                             SELECT id
                             FROM action_types
                         """).fetchall()
        ]

        for action_type in default_action_types:
            # Skip migration by condition
            if action_type['id'] in existing_action_type_ids:
                continue

            # Perform migration
            db.session.execute("""
                          INSERT INTO action_types (id, admin_only, show_on_frontpage, show_in_navbar, enable_labels, enable_files, enable_locations, enable_publications, enable_comments, enable_activity_log, enable_related_objects)
                          VALUES (:id, :admin_only, :show_on_frontpage, :show_in_navbar, :enable_labels, :enable_files, :enable_locations, :enable_publications, :enable_comments, :enable_activity_log, :enable_related_objects)
                      """, params=action_type)
            performed_migration = True

        return performed_migration
