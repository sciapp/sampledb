# coding: utf-8
"""

"""

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

import pytest

from sampledb import db, models
from sampledb.logic import errors, languages, settings, users


def test_create_language():
    language = languages.create_language(
        names={
            'en': "Other Language",
            'xy': "Other Language 2"
        },
        lang_code="xy",
        datetime_format_datetime='%Y-%m-%d %H:%M:%S',
        datetime_format_moment='YYYY-MM-DD HH:mm:ss',
        datetime_format_moment_output='lll',
        enabled_for_input=True,
        enabled_for_user_interface=True
    )

    assert language.names == {
        'en': "Other Language",
        'xy': "Other Language 2"
    }
    assert language.lang_code == "xy"
    assert language.datetime_format_datetime == '%Y-%m-%d %H:%M:%S'
    assert language.datetime_format_moment == 'YYYY-MM-DD HH:mm:ss'
    assert language.datetime_format_moment_output == 'lll'
    assert language.enabled_for_input is True


def test_create_existing_language():
    with pytest.raises(errors.LanguageAlreadyExistsError):
        languages.create_language(
            names={
                'en': "Other Language",
                'de': "Other Language"
            },
            lang_code="de",
            datetime_format_datetime='%Y-%m-%d %H:%M:%S',
            datetime_format_moment='YYYY-MM-DD HH:mm:ss',
            datetime_format_moment_output='lll',
            enabled_for_input=True,
            enabled_for_user_interface=True
        )


def test_create_language_with_unknown_name_translation():
    with pytest.raises(errors.LanguageDoesNotExistError):
        languages.create_language(
            names={
                'en': "Other Language",
                'xy': "Other Language 2",
                'yz': "Other Language 3"
            },
            lang_code="xy",
            datetime_format_datetime='%Y-%m-%d %H:%M:%S',
            datetime_format_moment='YYYY-MM-DD HH:mm:ss',
            datetime_format_moment_output='lll',
            enabled_for_input=True,
        enabled_for_user_interface=True
        )


def test_update_language():
    language = languages.create_language(
        names={
            'en': "Other Language",
            'xy': "Other Language 2"
        },
        lang_code="xy",
        datetime_format_datetime='%Y-%m-%d %H:%M:%S',
        datetime_format_moment='YYYY-MM-DD HH:mm:ss',
        datetime_format_moment_output='lll',
        enabled_for_input=True,
        enabled_for_user_interface=True
    )

    languages.update_language(
        language_id=language.id,
        names={
            'en': "Other Language",
            'yz': "Other Language 2"
        },
        lang_code="yz",
        datetime_format_datetime='%Y-%m-%d %H:%M:%S',
        datetime_format_moment='YYYY-MM-DD HH:mm:ss',
        datetime_format_moment_output='lll',
        enabled_for_input=False,
        enabled_for_user_interface=True
    )
    with pytest.raises(errors.LanguageDoesNotExistError):
        languages.get_language_by_lang_code('xy')
    language = languages.get_language_by_lang_code('yz')

    assert language.names == {
        'en': "Other Language",
        'yz': "Other Language 2"
    }
    assert language.lang_code == "yz"
    assert language.datetime_format_datetime == '%Y-%m-%d %H:%M:%S'
    assert language.datetime_format_moment == 'YYYY-MM-DD HH:mm:ss'
    assert language.datetime_format_moment_output == 'lll'
    assert language.enabled_for_input is False


def test_update_language_with_known_lang_code():
    language = languages.create_language(
        names={
            'en': "Other Language",
            'xy': "Other Language 2"
        },
        lang_code="xy",
        datetime_format_datetime='%Y-%m-%d %H:%M:%S',
        datetime_format_moment='YYYY-MM-DD HH:mm:ss',
        datetime_format_moment_output='lll',
        enabled_for_input=True,
        enabled_for_user_interface=True
    )
    with pytest.raises(errors.LanguageAlreadyExistsError):
        languages.update_language(
            language_id=language.id,
            names={
                'en': "Other Language"
            },
            lang_code="en",
            datetime_format_datetime='%Y-%m-%d %H:%M:%S',
            datetime_format_moment='YYYY-MM-DD HH:mm:ss',
            datetime_format_moment_output='lll',
            enabled_for_input=False,
            enabled_for_user_interface=True
        )


def test_update_language_with_unknown_name_translation():
    with pytest.raises(errors.LanguageDoesNotExistError):
        languages.update_language(
            language_id=languages.Language.GERMAN,
            names={
                'en': "Other Language",
                'xy': "Other Language 2",
                'yz': "Other Language 3"
            },
            lang_code="de",
            datetime_format_datetime='%Y-%m-%d %H:%M:%S',
            datetime_format_moment='YYYY-MM-DD HH:mm:ss',
            datetime_format_moment_output='lll',
            enabled_for_input=True,
            enabled_for_user_interface=True
        )


def test_update_language_with_locale_lang_code():
    with pytest.raises(errors.LanguageAlreadyExistsError):
        languages.update_language(
            language_id=languages.Language.GERMAN,
            names={
                'en': "Other Language",
                'de': "Other Language 2"
            },
            lang_code="xy",
            datetime_format_datetime='%Y-%m-%d %H:%M:%S',
            datetime_format_moment='YYYY-MM-DD HH:mm:ss',
            datetime_format_moment_output='lll',
            enabled_for_input=True,
            enabled_for_user_interface=True
        )


def test_get_language():
    assert languages.get_language(languages.Language.ENGLISH).lang_code == 'en'

    with pytest.raises(errors.LanguageDoesNotExistError):
        languages.get_language(42)


def test_get_languages():
    for language in languages.get_languages(only_enabled_for_input=True):
        assert language.enabled_for_input

    for language in models.languages.Language.query.all():
        language.enabled_for_input = True
        db.session.add(language)
    db.session.commit()

    num_languages = len(languages.get_languages())
    num_languages_for_input = len(languages.get_languages(only_enabled_for_input=True))
    assert num_languages_for_input == num_languages

    language = models.languages.Language.query.filter_by(lang_code='de').first()
    language.enabled_for_input = False
    db.session.add(language)
    db.session.commit()

    assert len(languages.get_languages()) == num_languages
    assert len(languages.get_languages(only_enabled_for_input=True)) == num_languages_for_input - 1

    assert any(
        language.lang_code == 'de'
        for language in languages.get_languages()
    )

    assert all(
        language.lang_code != 'de'
        for language in languages.get_languages(only_enabled_for_input=True)
    )


def test_get_user_language():
    english = languages.get_language_by_lang_code('en')
    german = languages.get_language_by_lang_code('de')

    assert languages.get_user_language(None) == english

    user = models.User(
        name="Example User",
        email="example@example.org",
        type=models.UserType.PERSON
    )
    db.session.add(user)
    db.session.commit()
    user = users.get_user(user.id)
    assert getattr(user, 'language', None) is None

    assert languages.get_user_language(user) == english
    assert getattr(user, 'language', None) == english

    settings.set_user_settings(user.id, {'LOCALE': 'de', 'AUTO_LC': False})
    assert languages.get_user_language(user) == english

    delattr(user, 'language')
    assert languages.get_user_language(user) == german
    assert getattr(user, 'language', None) == german

    delattr(user, 'language')
    settings.set_user_settings(user.id, {'LOCALE': 'xy'})
    assert languages.get_user_language(user) == english
    assert getattr(user, 'language', None) == english


def test_get_languages_in_object_data():
    data = {
        "name": {
            "_type": "text",
            "text": {"en": "OMBE-1"}
        },
        "array": [
            {
                "value": {
                    "_type": "text",
                    "text": {"de": "OMBE-1"}
                },
            },
            {
                "value": {
                    "_type": "text",
                    "text": {"xy": "OMBE-1"}
                },
            }
        ]
    }
    assert languages.get_languages_in_object_data(data) == {
        'en', 'de', 'xy'
    }
