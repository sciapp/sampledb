# coding: utf-8
"""

"""

import pytest

import sampledb
from sampledb.logic import actions, action_type_translations, errors


def test_set_action_type_translation():
    action_type = actions.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
    )
    action_type_translations.set_action_type_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_type_id=action_type.id,
        name="Example Action Type",
        description="This is an example action type",
        object_name="Object 1",
        object_name_plural="Objects 1",
        view_text="View Objects 1",
        perform_text="Create Object 1"
    )
    action_type_translation = action_type_translations.get_action_type_translation_for_action_type_in_language(
        action_type_id=action_type.id,
        language_id=sampledb.logic.languages.Language.ENGLISH
    )
    assert action_type_translation.name == "Example Action Type"
    assert action_type_translation.description == "This is an example action type"
    assert action_type_translation.object_name == "Object 1"
    assert action_type_translation.object_name_plural == "Objects 1"
    assert action_type_translation.view_text == "View Objects 1"
    assert action_type_translation.perform_text == "Create Object 1"

    action_type_translations.set_action_type_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_type_id=action_type.id,
        name="Example Action Type 2",
        description="This is an example action type 2",
        object_name="Object 2",
        object_name_plural="Objects 2",
        view_text="View Objects 2",
        perform_text="Create Object 2"
    )
    action_type_translation = action_type_translations.get_action_type_translation_for_action_type_in_language(
        action_type_id=action_type.id,
        language_id=sampledb.logic.languages.Language.ENGLISH
    )
    assert action_type_translation.name == "Example Action Type 2"
    assert action_type_translation.description == "This is an example action type 2"
    assert action_type_translation.object_name == "Object 2"
    assert action_type_translation.object_name_plural == "Objects 2"
    assert action_type_translation.view_text == "View Objects 2"
    assert action_type_translation.perform_text == "Create Object 2"

    with pytest.raises(errors.LanguageDoesNotExistError):
        action_type_translations.set_action_type_translation(
            language_id=42,
            action_type_id=action_type.id,
            name="Example Action Type 2",
            description="This is an example action type 2",
            object_name="Object 2",
            object_name_plural="Objects 2",
            view_text="View Objects 2",
            perform_text="Create Object 2"
        )
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        action_type_translations.set_action_type_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_type_id=action_type.id + 1,
            name="Example Action Type 2",
            description="This is an example action type 2",
            object_name="Object 2",
            object_name_plural="Objects 2",
            view_text="View Objects 2",
            perform_text="Create Object 2"
        )


def test_get_action_translations_for_action():
    action_type = actions.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
    )
    assert not action_type_translations.get_action_type_translations_for_action_type(action_type.id)

    assert len(action_type_translations.get_action_type_translations_for_action_type(action_type.id, use_fallback=True)) == 1
    action_type_translation = action_type_translations.get_action_type_translations_for_action_type(action_type.id, use_fallback=True)[0]
    assert action_type_translation.name == f"#{action_type.id}"
    assert action_type_translation.description == ''
    assert action_type_translation.object_name == 'Object'
    assert action_type_translation.object_name_plural == 'Objects'
    assert action_type_translation.view_text == 'View Objects'
    assert action_type_translation.perform_text == 'Create Object'

    action_type_translations.set_action_type_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_type_id=action_type.id,
        name="Example Action Type",
        description="This is an example action type",
        object_name="Object 1",
        object_name_plural="Objects 1",
        view_text="View Objects 1",
        perform_text="Create Object 1"
    )
    assert len(action_type_translations.get_action_type_translations_for_action_type(action_type.id)) == 1
    action_type_translation = action_type_translations.get_action_type_translations_for_action_type(action_type.id)[0]
    assert action_type_translation.name == "Example Action Type"

    action_type_translations.set_action_type_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_type_id=action_type.id,
        name="Example Action Type",
        description="This is an example action type",
        object_name="Object 2",
        object_name_plural="Objects 2",
        view_text="View Objects 2",
        perform_text="Create Object 2"
    )
    assert len(action_type_translations.get_action_type_translations_for_action_type(action_type.id)) == 2


def test_get_action_translation_for_action_in_language():
    action_type = actions.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
    )
    with pytest.raises(errors.ActionTypeTranslationDoesNotExistError):
        action_type_translations.get_action_type_translation_for_action_type_in_language(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_type_id=action_type.id,
        )

    action_type_translation = action_type_translations.get_action_type_translation_for_action_type_in_language(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_type_id=action_type.id,
        use_fallback=True
    )
    assert action_type_translation.language.lang_code == 'en'
    assert action_type_translation.name == f'#{action_type.id}'
    assert action_type_translation.description == ''

    action_type_translations.set_action_type_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_type_id=action_type.id,
        name="Example Action Type",
        description="This is an example action type",
        object_name='Example',
        object_name_plural='Examples',
        view_text='View Examples',
        perform_text='Define Example'
    )
    action_type_translation = action_type_translations.get_action_type_translation_for_action_type_in_language(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_type_id=action_type.id,
    )
    assert action_type_translation.name == "Example Action Type"
    assert action_type_translation.description == "This is an example action type"

    action_type_translation = action_type_translations.get_action_type_translation_for_action_type_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_type_id=action_type.id,
        use_fallback=True
    )
    assert action_type_translation.name == "Example Action Type"
    assert action_type_translation.description == "This is an example action type"

    action_type_translations.set_action_type_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_type_id=action_type.id,
        name="Beispielaktionstyp",
        description="Dies ist ein Beispielaktionstyp",
        object_name='Beispiel',
        object_name_plural='Beispiele',
        view_text='Beispiele anzeigen',
        perform_text='Beispiel definieren'
    )

    action_type_translation = action_type_translations.get_action_type_translation_for_action_type_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_type_id=action_type.id,
        use_fallback=True
    )
    assert action_type_translation.name == "Beispielaktionstyp"
    assert action_type_translation.description == "Dies ist ein Beispielaktionstyp"

    action_type_translations.set_action_type_translation(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_type_id=action_type.id,
        name="",
        description="Dies ist ein Beispielaktionstyp",
        object_name='Beispiel',
        object_name_plural='Beispiele',
        view_text='',
        perform_text='Beispiel definieren'
    )

    action_type_translation = action_type_translations.get_action_type_translation_for_action_type_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_type_id=action_type.id,
        use_fallback=True
    )
    assert action_type_translation.name == "Example Action Type"
    assert action_type_translation.description == "Dies ist ein Beispielaktionstyp"
    assert action_type_translation.view_text == "View Examples"

    action_type_translation = action_type_translations.get_action_type_translation_for_action_type_in_language(
        language_id=sampledb.logic.languages.Language.GERMAN,
        action_type_id=action_type.id,
        use_fallback=False
    )
    assert action_type_translation.name == ""
    assert action_type_translation.description == "Dies ist ein Beispielaktionstyp"
    assert action_type_translation.view_text == ""


def test_delete_action_translation():
    action_type = actions.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
    )
    action_type_translations.set_action_type_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_type_id=action_type.id,
        name="Example Action Type",
        description="This is an example action type",
        object_name="Object",
        object_name_plural="Objects",
        view_text="View Objects",
        perform_text="Create Object"
    )
    assert len(action_type_translations.get_action_type_translations_for_action_type(action_type.id)) == 1
    action_type_translations.delete_action_type_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_type_id=action_type.id
    )
    assert len(action_type_translations.get_action_type_translations_for_action_type(action_type.id)) == 0
    with pytest.raises(errors.ActionTypeTranslationDoesNotExistError):
        action_type_translations.delete_action_type_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_type_id=action_type.id
        )
