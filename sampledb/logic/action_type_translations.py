# coding: utf-8
"""
Logic module for management of action type translations

Action type translations contain all language-dependent attributes of an
action type for a specific language.
"""

import collections
import typing

from .actions import get_action_types, ActionType
from .. import db
from . import errors, languages, actions
from ..logic.languages import Language
from .. import models


class ActionTypeTranslation(collections.namedtuple(
    'ActionTypeTranslation', ['action_type_id', 'language_id', 'name', 'description', 'object_name', 'object_name_plural', 'view_text', 'perform_text']
)):
    """
    This class provides an immutable wrapper around models.action_translations.ActionTypeTranslation.
    """

    def __new__(cls, action_type_id: int, language_id: int, name: str, description: str, object_name: str, object_name_plural: str, view_text: str, perform_text: str):
        self = super(ActionTypeTranslation, cls).__new__(cls, action_type_id, language_id, name, description, object_name, object_name_plural, view_text, perform_text)
        self._language = None
        return self

    @classmethod
    def from_database(cls, action_type_translation: models.ActionTypeTranslation) -> 'ActionTypeTranslation':
        return ActionTypeTranslation(
            action_type_id=action_type_translation.action_type_id,
            language_id=action_type_translation.language_id,
            name=action_type_translation.name,
            description=action_type_translation.description,
            object_name=action_type_translation.object_name,
            object_name_plural=action_type_translation.object_name_plural,
            view_text=action_type_translation.view_text,
            perform_text=action_type_translation.perform_text
        )

    @property
    def language(self):
        if self._language is None:
            self._language = languages.get_language(self.language_id)
        return self._language


def get_action_type_translations_for_action_type(
        action_type_id: int,
        use_fallback: bool = False
) -> typing.List[ActionTypeTranslation]:
    """
    Return the action type with the given action type ID and all translations for this action type.

    :param action_type_id: the ID of an existing action type
    :return: the action type
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    :raise errors.ActionTypeTranslationDoesNotExistError: when no action type translation exists
        for the given action type
    """
    action_type_translations = models.ActionTypeTranslation.query.filter_by(
        action_type_id=action_type_id
    ).order_by(models.ActionTypeTranslation.language_id).all()
    if not action_type_translations and use_fallback:
        return [
            ActionTypeTranslation(
                action_type_id=action_type_id,
                language_id=Language.ENGLISH,
                name=f'#{action_type_id}',
                description='',
                object_name='Object',
                object_name_plural='Objects',
                view_text='View Objects',
                perform_text='Create Object'
            )
        ]
    return [
        ActionTypeTranslation.from_database(action_type_translation)
        for action_type_translation in action_type_translations
    ]


def get_action_type_translation_for_action_type_in_language(
        action_type_id: int,
        language_id: int,
        use_fallback: bool = False
) -> ActionTypeTranslation:
    """
    Returns a translation for given action type ID in language. If there is no translation in the given language,
    the english translation will be returned
    :param action_type_id: the ID of an existing action_type
    :param language_id: the ID of an existing language
    :return: a single translation for the action type in the given language or in English if there is no translation
        for the given language
    :raise errors.ActionTypeTranslationDoesNotExistError: when there is no translation or no translation in language and
        and not in English
    """

    action_type_translation = models.ActionTypeTranslation.query.filter_by(
        action_type_id=action_type_id,
        language_id=language_id
    ).first()
    if not use_fallback:
        if action_type_translation is None:
            raise errors.ActionTypeTranslationDoesNotExistError()
        else:
            return ActionTypeTranslation.from_database(action_type_translation)

    if language_id == Language.ENGLISH:
        english_translation = action_type_translation
    else:
        english_translation = models.ActionTypeTranslation.query.filter_by(
            action_type_id=action_type_id,
            language_id=Language.ENGLISH
        ).first()

    result_translation = ActionTypeTranslation(
        action_type_id=action_type_id,
        language_id=language_id if action_type_translation is not None else Language.ENGLISH,
        name=f'#{action_type_id}',
        description='',
        object_name='Object',
        object_name_plural='Objects',
        view_text='View Objects',
        perform_text='Create Object'
    )

    if action_type_translation is not None and action_type_translation.name:
        result_translation = result_translation._replace(name=action_type_translation.name)
    elif english_translation is not None and english_translation.name:
        result_translation = result_translation._replace(name=english_translation.name)

    if action_type_translation is not None and action_type_translation.description:
        result_translation = result_translation._replace(description=action_type_translation.description)
    elif english_translation is not None and english_translation.description:
        result_translation = result_translation._replace(description=english_translation.description)

    if action_type_translation is not None and action_type_translation.object_name:
        result_translation = result_translation._replace(object_name=action_type_translation.object_name)
    elif english_translation is not None and english_translation.object_name:
        result_translation = result_translation._replace(object_name=english_translation.object_name)

    if action_type_translation is not None and action_type_translation.object_name_plural:
        result_translation = result_translation._replace(object_name_plural=action_type_translation.object_name_plural)
    elif english_translation is not None and english_translation.object_name_plural:
        result_translation = result_translation._replace(object_name_plural=english_translation.object_name_plural)

    if action_type_translation is not None and action_type_translation.view_text:
        result_translation = result_translation._replace(view_text=action_type_translation.view_text)
    elif english_translation is not None and english_translation.view_text:
        result_translation = result_translation._replace(view_text=english_translation.view_text)

    if action_type_translation is not None and action_type_translation.perform_text:
        result_translation = result_translation._replace(perform_text=action_type_translation.perform_text)
    elif english_translation is not None and english_translation.perform_text:
        result_translation = result_translation._replace(perform_text=english_translation.perform_text)

    return result_translation


def set_action_type_translation(
        action_type_id: int,
        language_id: int,
        name: str,
        description: str,
        object_name: str,
        object_name_plural: str,
        view_text: str,
        perform_text: str
) -> ActionTypeTranslation:
    """
    Create or update an action type translation.

    :param action_type_id: the ID of the action type
    :param language_id: the ID of the language
    :param name: the name of the action type
    :param description: the description of the action type
    :param object_name: the name of an object created by an action of this type
    :param object_name_plural: the plural form of the object name
    :param view_text: the text to display for viewing objects created by actions of this type
    :param perform_text: the text to display for performing actions of this type
    :return: the action type translation
    :raise errors.LanguageDoesNotExistError: if no language with the given ID
        exists
    :raise errors.ActionTypeDoesNotExistError: if no action type with the
        given ID exists
    """
    action_type_translation = models.ActionTypeTranslation.query.filter_by(
        action_type_id=action_type_id,
        language_id=language_id
    ).first()
    if action_type_translation is None:
        actions.get_action_type(action_type_id)
        languages.get_language(language_id)
        action_type_translation = models.ActionTypeTranslation(
            action_type_id=action_type_id,
            language_id=language_id,
            name=name,
            description=description,
            object_name=object_name,
            object_name_plural=object_name_plural,
            view_text=view_text,
            perform_text=perform_text
        )
    else:
        action_type_translation.name = name
        action_type_translation.description = description
        action_type_translation.object_name = object_name
        action_type_translation.object_name_plural = object_name_plural
        action_type_translation.view_text = view_text
        action_type_translation.perform_text = perform_text
    db.session.add(action_type_translation)
    db.session.commit()
    return ActionTypeTranslation.from_database(action_type_translation)


def delete_action_type_translation(
        action_type_id: int,
        language_id: int
):
    """
    Deletes the action type translation with the given action type translation ID

    :param action_type_translation_id: the ID of an existing action type translation
    :raise errors.ActionTypeTranslationDoesNotExistError: when no action type translation exist for the given
        action type ID
    """
    action_type_translation = models.ActionTypeTranslation.query.filter_by(
        action_type_id=action_type_id,
        language_id=language_id
    ).first()
    if action_type_translation is None:
        raise errors.ActionTypeTranslationDoesNotExistError()
    db.session.delete(action_type_translation)
    db.session.commit()


def get_action_types_with_translations():
    """
    Return the list of all existing action types with their translations and a list of available languages

    :return: a list containing all action types which have translations and languages as attributes
    """

    action_types = get_action_types()
    for action_type in action_types:
        translations = get_action_type_translations_for_action_type(action_type.id)
        languages = [lang.language for lang in translations]
        setattr(action_type, 'translations', translations)
        setattr(action_type, 'languages', languages)
    return action_types


def get_action_types_with_translations_in_language(
        language_id: int
) -> typing.List[ActionType]:
    """
    Returns all action types with a single translation each in a given language or the users language

    :param language_id: the ID of an existing language
    :return: a list containing all action types which have a single translation as an additional attribute
        called translation.
    :raise errors.LanguageDoesNotExistError: when the language does not exist
    """
    action_types = get_action_types()

    for action_type in action_types:
        setattr(action_type, 'translation', get_action_type_translation_for_action_type_in_language(action_type.id, language_id, use_fallback=True))
    return action_types


def get_action_type_with_translations(action_type_id: int) -> ActionType:
    """
    Returns the action type with the given action type ID. The returned action type will have two additional
    attributes: translations and languages, translations contains all translations in a list and languages all languages

    :param action_type_id: the ID of an existing action type
    :return the action type with all of its translations
    :raise errors.ActionTypeDoesNotExistError: when no action type exists with the given ID
    """
    action_type = models.ActionType.query.get(action_type_id)
    if action_type is None:
        raise errors.ActionTypeDoesNotExistError()

    translations = get_action_type_translations_for_action_type(action_type.id)
    languages = [lang.language for lang in translations]
    setattr(action_type, 'translations', translations)
    setattr(action_type, 'languages', languages)

    return action_type


def get_action_type_with_translation_in_language(
        action_type_id: int,
        language_id: int
) -> ActionType:
    """
    Return an action with its translation for a specific language. If there is no translation for the given language,
    it will use the default english US translation

    :param action_type_id: the ID of an existing action_type
    :param language_id: the ID of an existing language
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    :raise errors.ActionTypeTranslationDoesNotExistError: When no translation for the given action type exists
    """
    action_type = models.ActionType.query.get(action_type_id)
    if action_type is None:
        raise errors.ActionTypeDoesNotExistError()

    translation = get_action_type_translation_for_action_type_in_language(
        action_type_id=action_type_id,
        language_id=language_id,
        use_fallback=True
    )
    if translation is None:
        raise errors.ActionTypeTranslationDoesNotExistError()
    setattr(action_type, 'translation', translation)
    return action_type
