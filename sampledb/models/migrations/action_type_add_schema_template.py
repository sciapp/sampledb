# coding: utf-8
"""
Create default action type for schema templates.
"""

import flask_sqlalchemy

from ..actions import ActionType
from ..languages import Language
from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Add TEMPLATE to default action types
    existing_action_type_ids = [
        action_type[0]
        for action_type in db.session.execute(db.text("""
                    SELECT id
                    FROM action_types;
                """)).fetchall()
    ]
    if ActionType.TEMPLATE in existing_action_type_ids:
        return False

    action_type_template = {
        'id': ActionType.TEMPLATE,
        'admin_only': False,
        'show_on_frontpage': False,
        'show_in_navbar': True,
        'enable_labels': True,
        'enable_files': True,
        'enable_locations': True,
        'enable_publications': True,
        'enable_comments': True,
        'enable_activity_log': True,
        'enable_related_objects': True,
        'enable_project_link': False,
        'disable_create_objects': True,
        'is_template': True
    }

    db.session.execute(db.text("""
      INSERT INTO action_types (id, admin_only, show_on_frontpage, show_in_navbar, enable_labels, enable_files, enable_locations, enable_publications, enable_comments, enable_activity_log, enable_related_objects, disable_create_objects, is_template)
      VALUES (:id, :admin_only, :show_on_frontpage, :show_in_navbar, :enable_labels, :enable_files, :enable_locations, :enable_publications, :enable_comments, :enable_activity_log, :enable_related_objects, :disable_create_objects, :is_template)
  """), params=action_type_template)
    performed_migration_type = True

    if table_has_column('action_types', 'show_in_object_filters'):
        # Hide schema template action type per default
        db.session.execute(db.text("""
            UPDATE action_types
            SET show_in_object_filters = FALSE
            WHERE id = :id
        """), params={'id': ActionType.TEMPLATE})

    # Add translations for TEMPLATE action type
    action_type_template_translations = [
        {
            'action_type_id': ActionType.TEMPLATE,
            'language_id': Language.ENGLISH,
            'name': 'Schema Template',
            'description': 'These Actions represent schema templates that can be included into other actions.',
            'object_name': '-',
            'object_name_plural': '-',
            'view_text': '-',
            'perform_text': '-'
        },
        {
            'action_type_id': ActionType.TEMPLATE,
            'language_id': Language.GERMAN,
            'name': 'Schema-Vorlage',
            'description': 'Aktionen dieses Typs können in andere Aktionen als Vorlagen für Schemata eingebunden werden.',
            'object_name': '-',
            'object_name_plural': '-',
            'view_text': '-',
            'perform_text': '-'
        }
    ]

    performed_migration_translation = False

    for template_translation in action_type_template_translations:
        db.session.execute(db.text("""
         INSERT INTO action_type_translations (action_type_id, language_id, name, description, object_name, object_name_plural, view_text, perform_text)
          VALUES (:action_type_id, :language_id,:name, :description, :object_name, :object_name_plural, :view_text, :perform_text)
      """), params=template_translation)
        performed_migration_translation = True

    return performed_migration_type and performed_migration_translation
