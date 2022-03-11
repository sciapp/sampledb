# coding: utf-8
"""

"""

import pytest

import sampledb
from sampledb.logic import instruments, instrument_translations, errors


def test_set_instrument_translation():
    instrument = instruments.create_instrument()
    instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Action",
        description="This is an example instrument",
        notes="Notes",
        short_description="Example"
    )
    instrument_translation = instrument_translations.get_instrument_translation_for_instrument_in_language(
        instrument_id=instrument.id,
        language_id=sampledb.logic.languages.Language.ENGLISH
    )
    assert instrument_translation.name == "Example Action"
    assert instrument_translation.description == "This is an example instrument"
    assert instrument_translation.notes == "Notes"
    assert instrument_translation.short_description == "Example"

    instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Action 2",
        description="This is an example instrument 2",
        notes="Notes 2",
        short_description="Example 2"
    )
    instrument_translation = instrument_translations.get_instrument_translation_for_instrument_in_language(
        instrument_id=instrument.id,
        language_id=sampledb.logic.languages.Language.ENGLISH
    )
    assert instrument_translation.name == "Example Action 2"
    assert instrument_translation.description == "This is an example instrument 2"
    assert instrument_translation.notes == "Notes 2"
    assert instrument_translation.short_description == "Example 2"

    with pytest.raises(errors.LanguageDoesNotExistError):
        instrument_translations.set_instrument_translation(
            language_id=42,
            instrument_id=instrument.id,
            name="Example Action 2",
            description="This is an example instrument 2",
            notes="Notes 2",
            short_description="Example 2"
        )
    with pytest.raises(errors.InstrumentDoesNotExistError):
        instrument_translations.set_instrument_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            instrument_id=instrument.id + 1,
            name="Example Action 2",
            description="This is an example instrument 2",
            notes="Notes 2",
            short_description="Example 2"
        )


def test_get_instrument_translations_for_instrument():
    instrument = instruments.create_instrument()
    assert not instrument_translations.get_instrument_translations_for_instrument(instrument.id)

    assert len(instrument_translations.get_instrument_translations_for_instrument(instrument.id, use_fallback=True)) == 1
    instrument_translation = instrument_translations.get_instrument_translations_for_instrument(instrument.id, use_fallback=True)[0]
    assert instrument_translation.name == f'Unnamed Instrument (#{instrument.id})'

    instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Action",
        description="This is an example instrument",
        notes="Notes",
        short_description="Example"
    )
    assert len(instrument_translations.get_instrument_translations_for_instrument(instrument.id)) == 1
    instrument_translation = instrument_translations.get_instrument_translations_for_instrument(instrument.id)[0]
    assert instrument_translation.name == "Example Action"

    instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        instrument_id=instrument.id,
        name="Example Action",
        description="This is an example instrument",
        short_description="Example",
        notes="Notes"
    )
    assert len(instrument_translations.get_instrument_translations_for_instrument(instrument.id)) == 2


def test_get_instrument_translation_for_instrument_in_language():
    instrument = instruments.create_instrument()
    with pytest.raises(errors.InstrumentTranslationDoesNotExistError):
        instrument_translations.get_instrument_translation_for_instrument_in_language(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            instrument_id=instrument.id,
        )

    instrument_translation = instrument_translations.get_instrument_translation_for_instrument_in_language(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        use_fallback=True
    )
    assert instrument_translation.language.lang_code == 'en'
    assert instrument_translation.name == f'Unnamed Instrument (#{instrument.id})'
    assert instrument_translation.description == ''
    assert instrument_translation.short_description == ''
    assert instrument_translation.notes == ''

    instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Action",
        description="This is an example instrument",
        short_description="Example",
        notes="Notes"
    )
    instrument_translation = instrument_translations.get_instrument_translation_for_instrument_in_language(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
    )
    assert instrument_translation.name == "Example Action"
    assert instrument_translation.description == "This is an example instrument"
    assert instrument_translation.short_description == "Example"
    assert instrument_translation.notes == "Notes"

    instrument_translation = instrument_translations.get_instrument_translation_for_instrument_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        instrument_id=instrument.id,
        use_fallback=True
    )
    assert instrument_translation.name == "Example Action"
    assert instrument_translation.description == "This is an example instrument"
    assert instrument_translation.short_description == "Example"

    instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        instrument_id=instrument.id,
        name="Beispielaktion",
        description="Dies ist eine Beispielaktion",
        short_description="Beispiel",
        notes="Notizen"
    )

    instrument_translation = instrument_translations.get_instrument_translation_for_instrument_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        instrument_id=instrument.id,
        use_fallback=True
    )
    assert instrument_translation.name == "Beispielaktion"
    assert instrument_translation.description == "Dies ist eine Beispielaktion"
    assert instrument_translation.short_description == "Beispiel"
    assert instrument_translation.notes == "Notizen"

    instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        instrument_id=instrument.id,
        name="",
        description="Dies ist eine Beispielaktion",
        short_description="",
        notes=""
    )

    instrument_translation = instrument_translations.get_instrument_translation_for_instrument_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        instrument_id=instrument.id,
        use_fallback=True
    )
    assert instrument_translation.name == "Example Action"
    assert instrument_translation.description == "Dies ist eine Beispielaktion"
    assert instrument_translation.short_description == "Example"
    assert instrument_translation.notes == "Notes"

    instrument_translation = instrument_translations.get_instrument_translation_for_instrument_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        instrument_id=instrument.id,
        use_fallback=False
    )
    assert instrument_translation.name == ""
    assert instrument_translation.description == "Dies ist eine Beispielaktion"
    assert instrument_translation.short_description == ""
    assert instrument_translation.notes == ""


def test_delete_instrument_translation():
    instrument = instruments.create_instrument()
    instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Action",
        description="This is an example instrument",
        short_description="Example",
        notes="Notes"
    )
    assert len(instrument_translations.get_instrument_translations_for_instrument(instrument.id)) == 1
    instrument_translations.delete_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id
    )
    assert len(instrument_translations.get_instrument_translations_for_instrument(instrument.id)) == 0
    with pytest.raises(errors.InstrumentTranslationDoesNotExistError):
        instrument_translations.delete_instrument_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            instrument_id=instrument.id
        )
