# coding: utf-8
"""
Create default languages.
"""

import json
import os

from ..languages import Language

MIGRATION_INDEX = 49
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    default_languages = [
        {
            'id': Language.ENGLISH,
            'names': json.dumps({
                'en': 'English',
                'de': 'Englisch'
            }),
            'lang_code': 'en',
            'datetime_format_datetime': '%Y-%m-%d %H:%M:%S',
            'datetime_format_moment': 'YYYY-MM-DD HH:mm:ss',
            'enabled_for_input': True,
        },
        {
            'id': Language.GERMAN,
            'names': json.dumps({
                'en': 'German',
                'de': 'Deutsch'
            }),
            'lang_code': 'de',
            'datetime_format_datetime': '%d.%m.%Y %H:%M:%S',
            'datetime_format_moment': 'DD.MM.YYYY HH:mm:ss',
            'enabled_for_input': False,
        }
    ]

    existing_language_ids = [
        language[0]
        for language in db.session.execute("""
               SELECT id
               FROM languages;
           """).fetchall()
    ]

    performed_migration = False
    for language in default_languages:
        # Skip migration by condition
        if language['id'] in existing_language_ids:
            continue

        # Perform migration
        db.session.execute("""
               INSERT INTO languages (id, names, lang_code, datetime_format_datetime, datetime_format_moment, enabled_for_input)
               VALUES (:id, :names, :lang_code, :datetime_format_datetime, :datetime_format_moment, :enabled_for_input);
           """, params=language)
        performed_migration = True

    languages_column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'languages'
    """).fetchall()
    if ('enabled_for_user_interface',) in languages_column_names:
        db.session.execute("""
            UPDATE languages
            SET enabled_for_user_interface = TRUE
            WHERE id < 0
        """)

    return performed_migration
