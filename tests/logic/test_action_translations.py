# coding: utf-8
"""

"""

import pytest

import sampledb
from sampledb.logic import actions, action_translations, errors

ACTION_SCHEMA = {
    'title': 'Object Information',
    'type': 'object',
    'properties': {
        'name': {
            'title': 'Name',
            'type': 'text'
        }
    },
    'required': ['name']
}


def test_set_action_translation():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=ACTION_SCHEMA
    )
    action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name="Example Action",
        description="This is an example action",
        short_description="Example"
    )
    action_translation = action_translations.get_action_translation_for_action_in_language(
        action_id=action.id,
        language_id=sampledb.logic.languages.Language.ENGLISH
    )
    assert action_translation.name == "Example Action"
    assert action_translation.description == "This is an example action"
    assert action_translation.short_description == "Example"

    action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name="Example Action 2",
        description="This is an example action 2",
        short_description="Example 2"
    )
    action_translation = action_translations.get_action_translation_for_action_in_language(
        action_id=action.id,
        language_id=sampledb.logic.languages.Language.ENGLISH
    )
    assert action_translation.name == "Example Action 2"
    assert action_translation.description == "This is an example action 2"
    assert action_translation.short_description == "Example 2"

    with pytest.raises(errors.LanguageDoesNotExistError):
        action_translations.set_action_translation(
            language_id=42,
            action_id=action.id,
            name="Example Action 2",
            description="This is an example action 2",
            short_description="Example 2"
        )
    with pytest.raises(errors.ActionDoesNotExistError):
        action_translations.set_action_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_id=action.id + 1,
            name="Example Action 2",
            description="This is an example action 2",
            short_description="Example 2"
        )


def test_get_action_translations_for_action():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=ACTION_SCHEMA
    )
    assert not action_translations.get_action_translations_for_action(action.id)

    assert len(action_translations.get_action_translations_for_action(action.id, use_fallback=True)) == 1
    action_translation = action_translations.get_action_translations_for_action(action.id, use_fallback=True)[0]
    assert action_translation.name == f'Unnamed Action (#{action.id})'

    action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name="Example Action",
        description="This is an example action",
        short_description="Example"
    )
    assert len(action_translations.get_action_translations_for_action(action.id)) == 1
    action_translation = action_translations.get_action_translations_for_action(action.id)[0]
    assert action_translation.name == "Example Action"

    action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_id=action.id,
        name="Example Action",
        description="This is an example action",
        short_description="Example"
    )
    assert len(action_translations.get_action_translations_for_action(action.id)) == 2


def test_get_action_translation_for_action_in_language():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=ACTION_SCHEMA
    )
    with pytest.raises(errors.ActionTranslationDoesNotExistError):
        action_translations.get_action_translation_for_action_in_language(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_id=action.id,
        )

    action_translation = action_translations.get_action_translation_for_action_in_language(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        use_fallback=True
    )
    assert action_translation.language.lang_code == 'en'
    assert action_translation.name == f'Unnamed Action (#{action.id})'
    assert action_translation.description == ''
    assert action_translation.short_description == ''

    action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name="Example Action",
        description="This is an example action",
        short_description="Example"
    )
    action_translation = action_translations.get_action_translation_for_action_in_language(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
    )
    assert action_translation.name == "Example Action"
    assert action_translation.description == "This is an example action"
    assert action_translation.short_description == "Example"

    action_translation = action_translations.get_action_translation_for_action_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_id=action.id,
        use_fallback=True
    )
    assert action_translation.name == "Example Action"
    assert action_translation.description == "This is an example action"
    assert action_translation.short_description == "Example"

    action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_id=action.id,
        name="Beispielaktion",
        description="Dies ist eine Beispielaktion",
        short_description="Beispiel"
    )

    action_translation = action_translations.get_action_translation_for_action_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_id=action.id,
        use_fallback=True
    )
    assert action_translation.name == "Beispielaktion"
    assert action_translation.description == "Dies ist eine Beispielaktion"
    assert action_translation.short_description == "Beispiel"

    action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_id=action.id,
        name="",
        description="Dies ist eine Beispielaktion",
        short_description=""
    )

    action_translation = action_translations.get_action_translation_for_action_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_id=action.id,
        use_fallback=True
    )
    assert action_translation.name == "Example Action"
    assert action_translation.description == "Dies ist eine Beispielaktion"
    assert action_translation.short_description == "Example"

    action_translation = action_translations.get_action_translation_for_action_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_id=action.id,
        use_fallback=False
    )
    assert action_translation.name == ""
    assert action_translation.description == "Dies ist eine Beispielaktion"
    assert action_translation.short_description == ""


def test_delete_action_translation():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=ACTION_SCHEMA
    )
    action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name="Example Action",
        description="This is an example action",
        short_description="Example"
    )
    assert len(action_translations.get_action_translations_for_action(action.id)) == 1
    action_translations.delete_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id
    )
    assert len(action_translations.get_action_translations_for_action(action.id)) == 0
    with pytest.raises(errors.ActionTranslationDoesNotExistError):
        action_translations.delete_action_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_id=action.id
        )
