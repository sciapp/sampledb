# coding: utf-8
"""
Logic module for management of action translations

Action translations contain all language-dependent attributes of an action
for a specific language.
"""

import dataclasses
import typing
from flask_babel import _

from .. import db
from . import errors, actions, languages
from .languages import Language
from .. import models


@dataclasses.dataclass(frozen=True)
class ActionTranslation:
    """
    This class provides an immutable wrapper around models.action_translations.ActionTranslation.
    """
    action_id: int
    language_id: int
    name: str
    description: str
    short_description: str
    _language_cache: typing.List[languages.Language] = dataclasses.field(default_factory=list, kw_only=True, repr=False, compare=False)

    @classmethod
    def from_database(cls, action_translation: models.ActionTranslation) -> 'ActionTranslation':
        return ActionTranslation(
            action_id=action_translation.action_id,
            language_id=action_translation.language_id,
            name=action_translation.name or '',
            description=action_translation.description or '',
            short_description=action_translation.short_description or ''
        )

    @property
    def language(self) -> Language:
        if not self._language_cache:
            self._language_cache.append(languages.get_language(self.language_id))
        return self._language_cache[0]


def set_action_translation(
        language_id: int,
        action_id: int,
        name: str,
        description: str = '',
        short_description: str = '',
) -> ActionTranslation:
    """
    Create or update an action translation.

    :param language_id: the ID of an existing language
    :param action_id: the ID of an existing action
    :param name: the name of the action
    :param description: a (possibly empty) description for the action
    :param short_description: the new (possibly empty) short description
    :return: the created action translation
    :raise errors.LanguageDoesNotExistError: if no language with the given ID
        exists
    :raise errors.ActionDoesNotExistError: if no action with the given ID
        exists
    """

    action_translation = models.ActionTranslation.query.filter_by(
        language_id=language_id,
        action_id=action_id
    ).first()
    if action_translation is None:
        actions.check_action_exists(action_id)
        languages.get_language(language_id)
        action_translation = models.ActionTranslation(
            language_id=language_id,
            action_id=action_id,
            name=name,
            description=description,
            short_description=short_description,
        )
    else:
        action_translation.name = name
        action_translation.description = description
        action_translation.short_description = short_description
    db.session.add(action_translation)
    db.session.commit()
    return ActionTranslation.from_database(action_translation)


def get_action_translations_for_action(
        action_id: int,
        use_fallback: bool = False
) -> typing.List[ActionTranslation]:
    """
    Return all action translations for the action with the given action ID.

    If no translations exist and use_fallback is True, a fallback english
    translation will be returned.

    :param action_id: the ID of an existing action
    :param use_fallback: whether a fallback translation may be returned
    :return: a list with all action translations
    """
    action_translations = models.ActionTranslation.query.filter_by(action_id=action_id).order_by(models.ActionTranslation.language_id).all()
    if not action_translations and use_fallback:
        return [
            ActionTranslation(
                action_id=action_id,
                language_id=Language.ENGLISH,
                name=_('Unnamed Action (#%(action_id)s)', action_id=action_id),
                description='',
                short_description=''
            )
        ]
    return [
        ActionTranslation.from_database(action_translation)
        for action_translation in action_translations
    ]


def get_action_translation_for_action_in_language(
        action_id: int,
        language_id: int,
        use_fallback: bool = False
) -> ActionTranslation:
    """
    Return a translation for the given action ID and language ID.

    If use_fallback is False, this will fail unless the requested translation
    exists. Otherwise, this will build a fallback translation, using english
    translation values if no values for the given language exist and using a
    default name if no english name exists.

    :param action_id: the ID of an existing action
    :param language_id: the ID of an existing language
    :param use_fallback: a fallback translation may be built
    :return: the requested action translation
    :raise errors.ActionTranslationDoesNotExistError: when the action
        translation does not exist and use_fallback was False
    """
    action_translation = models.ActionTranslation.query.filter_by(
        action_id=action_id,
        language_id=language_id
    ).first()
    if not use_fallback:
        if action_translation is None:
            raise errors.ActionTranslationDoesNotExistError()
        else:
            return ActionTranslation.from_database(action_translation)

    if language_id == Language.ENGLISH:
        english_translation = action_translation
    else:
        english_translation = models.ActionTranslation.query.filter_by(
            action_id=action_id,
            language_id=Language.ENGLISH
        ).first()

    name = _('Unnamed Action (#%(action_id)s)', action_id=action_id)
    if action_translation is not None and action_translation.name:
        name = action_translation.name
    elif english_translation is not None and english_translation.name:
        name = english_translation.name

    description = ''
    if action_translation is not None and action_translation.description:
        description = action_translation.description
    elif english_translation is not None and english_translation.description:
        description = english_translation.description

    short_description = ''
    if action_translation is not None and action_translation.short_description:
        short_description = action_translation.short_description
    elif english_translation is not None and english_translation.short_description:
        short_description = english_translation.short_description

    return ActionTranslation(
        action_id=action_id,
        language_id=language_id if action_translation is not None else Language.ENGLISH,
        name=name,
        description=description,
        short_description=short_description
    )


def delete_action_translation(
        language_id: int,
        action_id: int
) -> None:
    """
    Delete an action translation.

    :param language_id: the ID of an existing language
    :param action_id: the ID of an existing action
    :raise errors.ActionTranslationDoesNotExistError: when there is no action
        translation for the given IDs
    """
    action_translation = models.ActionTranslation.query.filter_by(
        language_id=language_id,
        action_id=action_id
    ).first()
    if action_translation is None:
        raise errors.ActionTranslationDoesNotExistError()

    db.session.delete(action_translation)
    db.session.commit()
