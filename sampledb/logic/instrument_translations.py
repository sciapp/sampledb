# coding: utf-8
"""
Logic module for management of instrument translations

Instrument translations complement instruments.
Translations contain all linguistic elements of instruments such as names.
"""

import collections
import typing

from .. import db
from ..models import Instrument, Language
from .. import models
from ..logic import errors, languages, instruments


class InstrumentTranslation(collections.namedtuple(
    'InstrumentTranslation', ['instrument_id', 'language_id', 'name', 'description', 'short_description', 'notes']
)):
    """
    This class provides an immutable wrapper around models.instrument_translations.InstrumentTranslation.
    """

    def __new__(cls, instrument_id: int, language_id: int, name: str, description: str, short_description: str, notes: str):
        self = super(InstrumentTranslation, cls).__new__(cls, instrument_id, language_id, name, description, short_description, notes)
        self._language = None
        return self

    @classmethod
    def from_database(cls, instrument_translation: models.InstrumentTranslation) -> 'InstrumentTranslation':
        return InstrumentTranslation(
            instrument_id=instrument_translation.instrument_id,
            language_id=instrument_translation.language_id,
            name=instrument_translation.name,
            description=instrument_translation.description,
            short_description=instrument_translation.short_description,
            notes=instrument_translation.notes
        )

    @property
    def language(self):
        if self._language is None:
            self._language = languages.get_language(self.language_id)
        return self._language


def set_instrument_translation(
        language_id: int,
        instrument_id: int,
        name: str,
        description: str,
        notes: str = '',
        short_description: str = ''
) -> InstrumentTranslation:
    """
    Creates a new instrument with the given name and description.

    :param language_id: the ID of an existing language
    :param instrument_id: the ID of an existing instrument
    :param name: the name of the instrument
    :param description: a (possibly empty) description of the instrument
    :param short_description: a (possibly empty) short description of the instrument
    :param notes: the notes shown to instrument responsible users
    :return: the new instrument translation
    """
    instrument_translation = models.InstrumentTranslation.query.filter_by(
        language_id=language_id,
        instrument_id=instrument_id
    ).first()
    if instrument_translation is None:
        instruments.get_instrument(instrument_id)
        languages.get_language(language_id)
        instrument_translation = models.InstrumentTranslation(
            language_id=language_id,
            instrument_id=instrument_id,
            name=name,
            description=description,
            notes=notes,
            short_description=short_description,
        )
    else:
        instrument_translation.language_id = language_id
        instrument_translation.name = name
        instrument_translation.description = description
        instrument_translation.short_description = short_description
        instrument_translation.notes = notes
    db.session.add(instrument_translation)
    db.session.commit()
    return InstrumentTranslation.from_database(instrument_translation)


def get_instrument_translations() -> typing.List[InstrumentTranslation]:
    """
    Returns all instrument translations.

    :return: a list of all instrument translations
    """
    return [
        InstrumentTranslation.from_database(instrument_translation)
        for instrument_translation in models.InstrumentTranslation.query.all()
    ]


def get_instrument_translations_for_instrument(instrument_id: int, use_fallback: bool = False) -> typing.List[InstrumentTranslation]:
    """
    Returns all instrument translations for an instrument

    :param instrument_id: the ID of an existing instrument
    :return: a list of all translations for an instrument
    :raise errors.InstrumentTranslationDoesNotExistError: when there is no translation for the given instrument
    """
    translations = models.InstrumentTranslation.query.filter_by(instrument_id=instrument_id).order_by(models.InstrumentTranslation.language_id).all()
    if not translations and use_fallback:
        return [
            InstrumentTranslation(
                instrument_id=instrument_id,
                language_id=Language.ENGLISH,
                name=f'#{instrument_id}',
                description='',
                short_description='',
                notes=''
            )
        ]
    return [
        InstrumentTranslation.from_database(instrument_translation)
        for instrument_translation in translations
    ]


def get_instrument_translation_for_instrument_in_language(
        instrument_id: int,
        language_id: int,
        use_fallback: bool = False
) -> InstrumentTranslation:
    """
    Returns an instrument translation with the given instrument ID and language.
    If the non english translation is not as complete as its english version, the missing parts will be
    added from the english version as attributes.
    If there is no translation for the given language the english translation will be returned.

    :param instrument_id: the ID of an existing instrument
    :param language_id: either the ID or the lang_code of an existing language
    :return: the instrument translation, which may contain additional english attributes such as english_name etc.
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    :raise errors.InstrumentTranslationDoesNotExistError: when no translation with the given language_id exists or
        when there is no english translation
    """
    instrument_translation = models.InstrumentTranslation.query.filter_by(
        instrument_id=instrument_id,
        language_id=language_id
    ).first()
    if not use_fallback:
        if instrument_translation is None:
            raise errors.InstrumentTranslationDoesNotExistError()
        else:
            return InstrumentTranslation.from_database(instrument_translation)

    if language_id == Language.ENGLISH:
        english_translation = instrument_translation
    else:
        english_translation = models.InstrumentTranslation.query.filter_by(
            instrument_id=instrument_id,
            language_id=Language.ENGLISH
        ).first()

    result_translation = InstrumentTranslation(
        instrument_id=instrument_id,
        language_id=language_id if instrument_translation is not None else Language.ENGLISH,
        name=f'#{instrument_id}',
        description='',
        short_description='',
        notes=''
    )

    if instrument_translation is not None and instrument_translation.name:
        result_translation = result_translation._replace(name=instrument_translation.name)
    elif english_translation is not None and english_translation.name:
        result_translation = result_translation._replace(name=english_translation.name)

    if instrument_translation is not None and instrument_translation.description:
        result_translation = result_translation._replace(description=instrument_translation.description)
    elif english_translation is not None and english_translation.description:
        result_translation = result_translation._replace(description=english_translation.description)

    if instrument_translation is not None and instrument_translation.short_description:
        result_translation = result_translation._replace(short_description=instrument_translation.short_description)
    elif english_translation is not None and english_translation.short_description:
        result_translation = result_translation._replace(short_description=english_translation.short_description)

    if instrument_translation is not None and instrument_translation.notes:
        result_translation = result_translation._replace(notes=instrument_translation.notes)
    elif english_translation is not None and english_translation.notes:
        result_translation = result_translation._replace(notes=english_translation.notes)

    return result_translation


def delete_instrument_translation(
        instrument_id: int,
        language_id: int
) -> None:
    """
    Delete an instrument translation.

    :param instrument_id: the ID of an existing instrument
    :param language_id: the ID of an existing language
    :raise errors.InstrumentTranslationDoesNotExistError: if there is no
        translation for the given instrument and language IDs
    """
    instrument_translation = models.InstrumentTranslation.query.filter_by(
        instrument_id=instrument_id,
        language_id=language_id
    ).first()
    if instrument_translation is None:
        raise errors.InstrumentTranslationDoesNotExistError()
    db.session.delete(instrument_translation)
    db.session.commit()


def get_instrument_with_translation_in_language(
        instrument_id: int,
        language_id: int
) -> Instrument:
    """
    Return the instrument with the given instrument ID and translation.

    :param instrument_id: the ID of an existing instrument
    :param language_id: the ID of an existing language
    :return: an instrument, with an additional attribute translation
    """

    instrument = instruments.get_instrument(instrument_id)
    setattr(instrument, 'translation', get_instrument_translation_for_instrument_in_language(
        instrument_id=instrument_id,
        language_id=language_id,
        use_fallback=True
    ))
    return instrument


def get_instruments_with_translation_in_language(language_id: int):
    """
    Return all instruments with a translation in the given language.

    :param language_id: the ID of an existing language
    :return: a list of instruments, with an additional attribute translation
    """
    return [
        get_instrument_with_translation_in_language(
            instrument_id=instrument.id,
            language_id=language_id
        )
        for instrument in Instrument.query.all()
    ]
