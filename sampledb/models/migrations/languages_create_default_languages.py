# coding: utf-8
"""
Create default languages.
"""

import json

import flask_sqlalchemy

from .utils import table_has_column
from ..languages import Language


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
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
        for language in db.session.execute(db.text("""
               SELECT id
               FROM languages;
           """)).fetchall()
    ]

    performed_migration = False
    for language in default_languages:
        # Skip migration by condition
        if language['id'] in existing_language_ids:
            continue

        # Perform migration
        db.session.execute(db.text("""
               INSERT INTO languages (id, names, lang_code, datetime_format_datetime, datetime_format_moment, enabled_for_input)
               VALUES (:id, :names, :lang_code, :datetime_format_datetime, :datetime_format_moment, :enabled_for_input);
           """), params=language)
        performed_migration = True

    if table_has_column('languages', 'enabled_for_user_interface'):
        db.session.execute(db.text("""
            UPDATE languages
            SET enabled_for_user_interface = TRUE
            WHERE id < 0
        """))
    if table_has_column('languages', 'datetime_format_moment_output'):
        db.session.execute(db.text("""
            UPDATE languages
            SET datetime_format_moment_output = 'MMM D, YYYY, h:mm:ss A'
            WHERE id = -99
        """))
        db.session.execute(db.text("""
            UPDATE languages
            SET datetime_format_moment_output = 'DD.MM.YYYY HH:mm:ss'
            WHERE id = -98
        """))
    if table_has_column('languages', 'date_format_moment_output'):
        db.session.execute(db.text("""
            UPDATE languages
            SET date_format_moment_output = 'MMM D, YYYY'
            WHERE id = -99
        """))
        db.session.execute(db.text("""
            UPDATE languages
            SET date_format_moment_output = 'DD.MM.YYYY'
            WHERE id = -98
        """))

    return performed_migration
