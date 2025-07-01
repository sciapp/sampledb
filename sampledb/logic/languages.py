# coding: utf-8
"""
Logic module for management of languages
"""

import dataclasses
import typing

from .caching import cache_per_request
from .. import db
from . import errors, settings, locale
from .. import models
if typing.TYPE_CHECKING:
    from .users import User


@dataclasses.dataclass(frozen=True)
class Language:
    """
    This class provides an immutable wrapper around models.languages.Language.
    """
    id: int
    lang_code: str
    names: typing.Dict[str, str]
    datetime_format_datetime: str
    datetime_format_moment: str
    datetime_format_moment_output: str
    date_format_moment_output: str
    enabled_for_input: bool
    enabled_for_user_interface: bool

    ENGLISH = models.Language.ENGLISH
    GERMAN = models.Language.GERMAN

    @staticmethod
    def from_database(language: models.Language) -> 'Language':
        return Language(
            id=language.id,
            lang_code=language.lang_code,
            names=language.names,
            datetime_format_datetime=language.datetime_format_datetime,
            datetime_format_moment=language.datetime_format_moment,
            datetime_format_moment_output=language.datetime_format_moment_output,
            date_format_moment_output=language.date_format_moment_output,
            enabled_for_input=language.enabled_for_input,
            enabled_for_user_interface=language.enabled_for_user_interface
        )


def create_language(
        *,
        names: typing.Dict[str, str],
        lang_code: str,
        datetime_format_datetime: str,
        datetime_format_moment: str,
        datetime_format_moment_output: str,
        date_format_moment_output: str,
        enabled_for_input: bool,
        enabled_for_user_interface: bool
) -> Language:
    """
    Create a new language.

    :param names: a dict containing the language's names in other languages
    :param lang_code: the language code
    :param datetime_format_datetime: format for datetime
    :param datetime_format_moment: format for moment
    :param datetime_format_moment_output: output format for moment
    :param date_format_moment_output: output format for moment for dates only
    :param enabled_for_input: whether the language is enabled for input
    :param enabled_for_user_interface: whether the language is enabled
        for the user interface
    :return: the new language
    :raise errors.LanguageAlreadyExistsError: if another language with this
        language code already exists
    :raise errors.LanguageDoesNotExistError: if the language name contains a
        translation for an unknown language code
    """
    if models.Language.query.filter_by(lang_code=lang_code).first() is not None:
        raise errors.LanguageAlreadyExistsError()

    all_language_codes = {
        language.lang_code
        for language in models.Language.query.all()
    }
    all_language_codes.add(lang_code)

    if set(names.keys()) - all_language_codes:
        raise errors.LanguageDoesNotExistError()

    language = models.Language(
        names=names,
        lang_code=lang_code,
        datetime_format_datetime=datetime_format_datetime,
        datetime_format_moment=datetime_format_moment,
        datetime_format_moment_output=datetime_format_moment_output,
        date_format_moment_output=date_format_moment_output,
        enabled_for_input=enabled_for_input,
        enabled_for_user_interface=enabled_for_user_interface
    )
    db.session.add(language)
    db.session.commit()
    return Language.from_database(language)


def update_language(
        language_id: int,
        names: typing.Dict[str, str],
        lang_code: str,
        datetime_format_datetime: str,
        datetime_format_moment: str,
        datetime_format_moment_output: str,
        date_format_moment_output: str,
        enabled_for_input: bool,
        enabled_for_user_interface: bool
) -> None:
    """
    Update a language.

    :param language_id: the id of the language
    :param names: a dict containing the language's names in other languages
    :param lang_code: the language code
    :param datetime_format_datetime: format for datetime
    :param datetime_format_moment: format for moment
    :param datetime_format_moment_output: format for moment output
    :param date_format_moment_output: output format for moment for dates only
    :param enabled_for_input: whether the language is enabled for input
    :param enabled_for_user_interface: whether the language is enabled
        for the user interface
    :raise errors.LanguageAlreadyExistsError: when the language code already
        exists for a different language or the current language code matches
        a supported locale language code
    :raise errors.LanguageDoesNotExistError: if the language name contains a
        translation for an unknown language code or the language itself does
        not exist
    """

    all_language_codes = {
        language.lang_code
        for language in models.Language.query.all()
    }
    all_language_codes.add(lang_code)

    language = models.Language.query.filter_by(id=language_id).first()
    if language is None:
        raise errors.LanguageDoesNotExistError()
    if language.lang_code != lang_code:
        if models.Language.query.filter_by(lang_code=lang_code).first() is not None:
            raise errors.LanguageAlreadyExistsError()
        if language.lang_code in locale.SUPPORTED_LOCALES:
            raise errors.LanguageAlreadyExistsError()
        all_language_codes.remove(language.lang_code)

    if set(names.keys()) - all_language_codes:
        raise errors.LanguageDoesNotExistError()

    language.names = names
    language.lang_code = lang_code
    language.datetime_format_datetime = datetime_format_datetime
    language.datetime_format_moment = datetime_format_moment
    language.datetime_format_moment_output = datetime_format_moment_output
    language.date_format_moment_output = date_format_moment_output
    language.enabled_for_input = enabled_for_input
    language.enabled_for_user_interface = enabled_for_user_interface
    db.session.add(language)
    db.session.commit()


def get_languages(
        only_enabled_for_input: bool = False
) -> typing.List[Language]:
    """
    Return all languages.

    :param only_enabled_for_input: if True, only return languages which are
        enabled for input

    :return: the list of all languages
    """
    language_query = models.Language.query
    if only_enabled_for_input:
        language_query = language_query.filter_by(enabled_for_input=True)
    language_query = language_query.order_by(models.Language.id)
    return [
        Language.from_database(language)
        for language in language_query.all()
    ]


def get_language(language_id: int) -> Language:
    """
    Returns the language with the given language ID.

    :param language_id: the ID of an existing language
    :return: the language
    :raise errors.LanguageDoesNotExistError: when no language with the given language ID exists
    """
    language = models.Language.query.filter_by(id=language_id).first()
    if language is None:
        raise errors.LanguageDoesNotExistError()
    return Language.from_database(language)


def get_language_by_lang_code(lang_code: str) -> Language:
    """
    Returns the language with the given lang_code.

    :param lang_code: the lang_code of an existing language
    :return: the language with the lang_code
    :raise errors.LanguageDoesNotExistError: when there is no language for the given lang code
    """
    language = models.Language.query.filter_by(lang_code=lang_code).first()

    if language is None:
        raise errors.LanguageDoesNotExistError()
    return Language.from_database(language)


@cache_per_request(key=lambda user: user.id if user else None)
def get_user_language(user: typing.Optional['User']) -> Language:
    """
    Return the language of the current user.

    :param user: the current user, or None
    :return: the user's language or english
    """
    if not user or not user.is_authenticated:
        try:
            return get_language_by_lang_code(locale.guess_request_locale())
        except errors.LanguageDoesNotExistError:
            return get_language(models.Language.ENGLISH)

    language = user.language_cache[0]
    if language is None:
        auto_lc = settings.get_user_setting(user.id, 'AUTO_LC')
        if auto_lc:
            language_code = locale.guess_request_locale()
        else:
            language_code = settings.get_user_setting(user.id, 'LOCALE')
        try:
            language = get_language_by_lang_code(language_code)
        except errors.LanguageDoesNotExistError:
            language = get_language(models.Language.ENGLISH)
        user.language_cache[0] = language
    return language


def get_languages_in_object_data(
        data: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]]
) -> typing.Set[str]:
    language_codes = set()

    if isinstance(data, dict):
        if '_type' in data:
            if data['_type'] == 'text' and isinstance(data.get('text'), dict):
                language_codes.update(set(data['text']))
        else:
            for property_data in data.values():
                language_codes.update(get_languages_in_object_data(property_data))

    if isinstance(data, list):
        for item_data in data:
            language_codes.update(get_languages_in_object_data(item_data))

    return language_codes


def filter_translations(
        translations: typing.Dict[str, str]
) -> typing.Dict[str, str]:
    allowed_language_codes = {
        language.lang_code
        for language in get_languages(only_enabled_for_input=True)
    }

    filtered_translations = {}
    for language_code, translation in translations.items():
        if language_code not in allowed_language_codes:
            raise errors.LanguageDoesNotExistError()
        if translation:
            filtered_translations[language_code] = translation

    return filtered_translations


def get_language_codes(
        only_enabled_for_input: bool = False,
        only_enabled_for_user_interface: bool = False
) -> typing.Set[str]:
    """
    Return a set of known language codes.

    :param only_enabled_for_input: only return codes for languages enabled
        for input
    :param only_enabled_for_user_interface: only return codes for languages
        enabled for the user interface
    :return: the set of language codes
    """
    query = models.Language.query
    if only_enabled_for_input:
        query = query.filter_by(enabled_for_input=True)
    if only_enabled_for_user_interface:
        query = query.filter_by(enabled_for_user_interface=True)
    language_code_tuples = query.with_entities(models.Language.lang_code).all()
    return {
        language_code_tuple[0]
        for language_code_tuple in language_code_tuples
    }
