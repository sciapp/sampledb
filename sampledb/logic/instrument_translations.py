# coding: utf-8
"""
Logic module for management of instrument translations

Instrument translations complement instruments.
Translations contain all linguistic elements of instruments such as names.
"""

import dataclasses
import typing
from flask_babel import _

from .. import db
from .languages import Language
from .. import models
from . import errors, languages, instruments


@dataclasses.dataclass(frozen=True)
class InstrumentTranslation:
    """
    This class provides an immutable wrapper around models.instrument_translations.InstrumentTranslation.
    """
    instrument_id: int
    language_id: int
    name: str
    description: str
    short_description: str
    notes: str
    _language_cache: typing.List[languages.Language] = dataclasses.field(default_factory=list, kw_only=True, repr=False, compare=False)

    @classmethod
    def from_database(cls, instrument_translation: models.InstrumentTranslation) -> 'InstrumentTranslation':
        return InstrumentTranslation(
            instrument_id=instrument_translation.instrument_id,
            language_id=instrument_translation.language_id,
            name=instrument_translation.name or '',
            description=instrument_translation.description or '',
            short_description=instrument_translation.short_description or '',
            notes=instrument_translation.notes or ''
        )

    @property
    def language(self) -> Language:
        if not self._language_cache:
            self._language_cache.append(languages.get_language(self.language_id))
        return self._language_cache[0]


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
        instruments.check_instrument_exists(instrument_id)
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


def get_instrument_translations_for_instrument(instrument_id: int, use_fallback: bool = False) -> typing.List[InstrumentTranslation]:
    """
    Returns all instrument translations for an instrument

    :param instrument_id: the ID of an existing instrument
    :param use_fallback: whether a fallback translation may be returned
    :return: a list of all translations for an instrument
    :raise errors.InstrumentTranslationDoesNotExistError: when there is no translation for the given instrument
    """
    translations = models.InstrumentTranslation.query.filter_by(instrument_id=instrument_id).order_by(models.InstrumentTranslation.language_id).all()
    if not translations and use_fallback:
        return [
            InstrumentTranslation(
                instrument_id=instrument_id,
                language_id=Language.ENGLISH,
                name=_('Unnamed Instrument (#%(instrument_id)s)', instrument_id=instrument_id),
                description='',
                short_description='',
                notes=''
            )
        ]
    return [
        InstrumentTranslation.from_database(instrument_translation)
        for instrument_translation in translations
    ]


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
