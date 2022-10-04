# coding: utf-8
"""
Logic module for management of action type translations

Action type translations contain all language-dependent attributes of an
action type for a specific language.
"""

import collections
import typing

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

    def __new__(
            cls,
            action_type_id: int,
            language_id: int,
            name: str,
            description: str,
            object_name: str,
            object_name_plural: str,
            view_text: str,
            perform_text: str
    ) -> 'ActionTypeTranslation':
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
    def language(self) -> Language:
        self._language: typing.Optional[Language]
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
) -> None:
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
