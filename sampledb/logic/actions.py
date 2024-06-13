# coding: utf-8
"""
Logic module for management of actions

Actions are used to represent all kinds of methods or processes that result
in the creation of a new sample or measurement. What kind of object is
created when performing an action is defined by the action's type. The
action's schema defines what information should or may be recorded in SampleDB
for a newly created object.

Actions can be related to an instrument, which serves both to group actions
together and to provide instrument responsible users with permissions for
samples or measurements created with their instrument.

Actions can also be user-defined, to allow advanced users to create actions
for instruments which would otherwise not be included.

As actions form the basis for objects, they cannot be deleted. However, an
action can be altered as long as the type and instrument stay the same.
"""

import copy
import dataclasses
import typing

from .. import db
from .. import models
from . import errors, instruments, users, schemas, components, topics, favorites
from .utils import cache, get_translated_text
from .action_types import check_action_type_exists, ActionType


@dataclasses.dataclass(frozen=True)
class Action:
    """
    This class provides an immutable wrapper around models.actions.Action.
    """
    id: int
    type_id: typing.Optional[int]
    type: typing.Optional['ActionType']
    instrument_id: typing.Optional[int]
    instrument: typing.Optional[instruments.Instrument]
    schema: typing.Optional[typing.Dict[str, typing.Any]]
    user_id: typing.Optional[int]
    user: typing.Optional[users.User]
    is_hidden: bool
    name: typing.Dict[str, str]
    description: typing.Dict[str, str]
    description_is_markdown: bool
    short_description: typing.Dict[str, str]
    short_description_is_markdown: bool
    fed_id: typing.Optional[int]
    component_id: typing.Optional[int]
    component: typing.Optional[components.Component]
    admin_only: bool
    disable_create_objects: bool
    objects_readable_by_all_users_by_default: bool
    topics: typing.List[topics.Topic]
    use_instrument_topics: bool

    @classmethod
    def from_database(cls, action: models.Action) -> 'Action':
        return Action(
            id=action.id,
            type_id=action.type_id,
            type=ActionType.from_database(action.type) if action.type is not None else None,
            instrument_id=action.instrument_id,
            instrument=instruments.Instrument.from_database(action.instrument) if action.instrument is not None else None,
            schema=copy.deepcopy(action.schema) if action.schema is not None else None,
            user_id=action.user_id,
            user=users.User.from_database(action.user) if action.user is not None else None,
            is_hidden=action.is_hidden,
            name=action.name,
            description=action.description,
            description_is_markdown=action.description_is_markdown,
            short_description=action.short_description,
            short_description_is_markdown=action.short_description_is_markdown,
            fed_id=action.fed_id,
            component_id=action.component_id,
            component=components.Component.from_database(action.component) if action.component is not None else None,
            admin_only=action.admin_only,
            disable_create_objects=action.disable_create_objects,
            objects_readable_by_all_users_by_default=action.objects_readable_by_all_users_by_default,
            topics=[topics.Topic.from_database(topic) for topic in (
                action.instrument.topics if action.instrument is not None and action.use_instrument_topics else action.topics
            )],
            use_instrument_topics=action.use_instrument_topics
        )

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(id={self.id!r})>"


@typing.overload
def create_action(
        *,
        action_type_id: int,
        schema: typing.Dict[str, typing.Any],
        instrument_id: typing.Optional[int] = None,
        user_id: typing.Optional[int] = None,
        description_is_markdown: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False,
        fed_id: None = None,
        component_id: None = None,
        admin_only: bool = False,
        disable_create_objects: bool = False,
        objects_readable_by_all_users_by_default: bool = False,
        strict_schema_validation: bool = True,
        use_instrument_topics: bool = False,
) -> Action:
    ...


@typing.overload
def create_action(
        *,
        action_type_id: typing.Optional[int],
        schema: typing.Optional[typing.Dict[str, typing.Any]],
        instrument_id: typing.Optional[int] = None,
        user_id: typing.Optional[int] = None,
        description_is_markdown: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False,
        fed_id: int,
        component_id: int,
        admin_only: bool = False,
        disable_create_objects: bool = False,
        objects_readable_by_all_users_by_default: bool = False,
        strict_schema_validation: bool = True,
        use_instrument_topics: bool = False,
) -> Action:
    ...


def create_action(
        *,
        action_type_id: typing.Optional[int],
        schema: typing.Optional[typing.Dict[str, typing.Any]],
        instrument_id: typing.Optional[int] = None,
        user_id: typing.Optional[int] = None,
        description_is_markdown: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None,
        admin_only: bool = False,
        disable_create_objects: bool = False,
        objects_readable_by_all_users_by_default: bool = False,
        strict_schema_validation: bool = True,
        use_instrument_topics: bool = False,
) -> Action:
    """
    Creates a new action with the given type and schema. If
    instrument_id is not None, the action will belong to the instrument with
    this ID.

    :param action_type_id: the ID of an existing action type
    :param schema: the schema for objects created using this action
    :param instrument_id: None or the ID of an existing instrument
    :param user_id: None or the ID of an existing user
    :param description_is_markdown: whether the description contains Markdown
    :param is_hidden: None or whether the action should be hidden
    :param short_description_is_markdown: whether the short description
        contains Markdown
    :param fed_id: the ID of the related action at the exporting component
    :param component_id: the ID of the exporting component
    :param admin_only: whether only admins may use the action to create objects
    :param disable_create_objects: whether the action may not be used to create objects
    :param objects_readable_by_all_users_by_default: whether objects created
        with this action should be readable by all signed-in users by default
    :param strict_schema_validation: whether schema validation should use strict mode
    :param use_instrument_topics: whether the topics of the instrument should be used
    :return: the created action
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    :raise errors.SchemaValidationError: when the schema is invalid
    :raise errors.InstrumentDoesNotExistError: when instrument_id is not None
        and no instrument with the given instrument ID exists
    :raise errors.UserDoesNotExistError: when user_id is not None and no user
        with the given user ID exists
    """
    assert (component_id is None) == (fed_id is None)
    assert component_id is not None or (action_type_id is not None and schema is not None)

    if action_type_id is not None:
        # ensure the action type exists
        check_action_type_exists(action_type_id)

    if schema is not None:
        schemas.validate_schema(schema, strict=strict_schema_validation)
    if instrument_id is not None:
        # ensure that the instrument can be found
        instruments.check_instrument_exists(instrument_id)
    if user_id is not None:
        # ensure that the user can be found
        users.check_user_exists(user_id)

    if component_id is not None:
        # ensure that the component can be found
        components.check_component_exists(component_id)

    action = models.Action(
        action_type_id=action_type_id,
        description_is_markdown=description_is_markdown,
        is_hidden=is_hidden,
        schema=schema,
        instrument_id=instrument_id,
        user_id=user_id,
        short_description_is_markdown=short_description_is_markdown,
        fed_id=fed_id,
        component_id=component_id,
        admin_only=admin_only,
        disable_create_objects=disable_create_objects,
        objects_readable_by_all_users_by_default=objects_readable_by_all_users_by_default,
        use_instrument_topics=use_instrument_topics if instrument_id is not None else False,
    )
    db.session.add(action)
    db.session.commit()
    return Action.from_database(action)


def get_actions(
        *,
        action_type_id: typing.Optional[int] = None,
        instrument_id: typing.Optional[int] = None,
) -> typing.List[Action]:
    """
    Returns all actions, optionally only actions of a given type.

    :param action_type_id: the ID of an existing action type, or None
    :param instrument_id: the ID of an existing instrument, or None
    :return: the list of actions
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    query = models.Action.query
    if action_type_id is not None:
        query = query.filter_by(type_id=action_type_id)
    if instrument_id is not None:
        query = query.filter_by(instrument_id=instrument_id)
    actions = query.all()
    if not actions:
        if action_type_id is not None:
            # ensure the action type exists
            check_action_type_exists(action_type_id=action_type_id)
        if instrument_id is not None:
            # ensure the instrument exists
            instruments.check_instrument_exists(instrument_id=instrument_id)
    return [
        Action.from_database(action)
        for action in actions
    ]


@cache
def check_action_exists(
        action_id: int
) -> None:
    """
    Check whether an action with the given action ID exists.

    :param action_id: the ID of an existing action
    :raise errors.ActionDoesNotExistError: when no action with the given
        action ID exists
    """
    if not db.session.query(db.exists().where(models.Action.id == action_id)).scalar():
        raise errors.ActionDoesNotExistError()


@cache
def get_action_owner_id(
        action_id: int
) -> typing.Optional[int]:
    """
    Get the owner of an action with a given ID.

    :param action_id: the ID of an existing action
    :return: the ID of the action's owner, or None
    :raise errors.ActionDoesNotExistError: when no action with the given
        action ID exists
    """
    row_or_none = db.session.query(models.Action.user_id).filter(models.Action.id == action_id).first()
    if row_or_none is None:
        raise errors.ActionDoesNotExistError()
    return typing.cast(typing.Optional[int], row_or_none[0])


def get_mutable_action(
        action_id: int,
        component_id: typing.Optional[int] = None
) -> models.Action:
    """
    Get the mutable action instance to perform changes in the database on.

    :param action_id: the ID of an existing action
    :param component_id: the ID of an existing component, or None
    :return: the mutable action
    :raise errors.ActionDoesNotExistError: when no action with the given
        action ID exists
    """
    action: typing.Optional[models.Action]
    if component_id is None:
        action = models.Action.query.filter_by(id=action_id).first()
    else:
        # ensure that the component can be found
        components.check_component_exists(component_id)
        action = models.Action.query.filter_by(fed_id=action_id, component_id=component_id).first()
    if action is None:
        raise errors.ActionDoesNotExistError()
    return action


def get_action(
        action_id: int,
        component_id: typing.Optional[int] = None
) -> Action:
    """
    Return the action with the given action ID.

    :param action_id: the ID of an existing action
    :param component_id: the ID of an existing component, or None
    :return: the action
    :raise errors.ActionDoesNotExistError: when no action with the given
        action ID exists
    """
    return Action.from_database(get_mutable_action(action_id, component_id))


def update_action(
        *,
        action_id: int,
        schema: typing.Optional[typing.Dict[str, typing.Any]],
        description_is_markdown: bool = False,
        is_hidden: typing.Optional[bool] = None,
        short_description_is_markdown: bool = False,
        admin_only: typing.Optional[bool] = None,
        disable_create_objects: typing.Optional[bool] = None,
        objects_readable_by_all_users_by_default: typing.Optional[bool] = None,
        use_instrument_topics: typing.Optional[bool] = None
) -> None:
    """
    Updates the action with the given action ID, setting its schema.

    :param action_id: the ID of an existing action
    :param schema: the new schema for objects created using this action
    :param description_is_markdown: whether the description contains Markdown
    :param is_hidden: None or whether the action should be hidden
    :param short_description_is_markdown: whether the short description
        contains Markdown
    :param admin_only: None or whether only admins may use the action to create objects
    :param disable_create_objects: None or whether the action may not be used to create objects
    :param objects_readable_by_all_users_by_default: whether objects created
        with this action should be readable by all signed-in users by default,
        or None
    :param use_instrument_topics: whether the topics of the instrument should be used, or None
    :raise errors.SchemaValidationError: when the schema is invalid
    :raise errors.InstrumentDoesNotExistError: when instrument_id is not None
        and no instrument with the given instrument ID exists
    """
    if schema is not None:
        schemas.validate_schema(schema, invalid_template_action_ids=[action_id], strict=True)
    action = get_mutable_action(action_id)
    action.description_is_markdown = description_is_markdown
    action.schema = schema
    action.short_description_is_markdown = short_description_is_markdown
    if is_hidden is not None:
        action.is_hidden = is_hidden
    if admin_only is not None:
        action.admin_only = admin_only
    if disable_create_objects is not None:
        action.disable_create_objects = disable_create_objects
    if objects_readable_by_all_users_by_default is not None:
        action.objects_readable_by_all_users_by_default = objects_readable_by_all_users_by_default
    if use_instrument_topics is not None:
        if action.instrument_id is not None or use_instrument_topics is False:
            action.use_instrument_topics = use_instrument_topics
    db.session.add(action)
    db.session.commit()
    update_actions_using_template_action(action_id)


def update_actions_using_template_action(
        template_action_id: int
) -> None:
    """
    Update the schemas of all actions using the given template action.

    :param template_action_id: the ID of a template action
    """
    template_action_schema = get_action(template_action_id).schema
    if template_action_schema is None:
        return
    template_action_schema = schemas.templates.process_template_action_schema(template_action_schema)
    actions = get_actions()
    updated_template_action_ids = []
    for action in actions:
        if action.id == template_action_id:
            continue
        if not action.schema:
            continue
        current_schema = copy.deepcopy(action.schema)
        updated_schema = schemas.templates.update_schema_using_template_action(current_schema, template_action_id, template_action_schema)
        if action.schema != updated_schema:
            try:
                schemas.validate_schema(updated_schema, strict=True)
            except errors.ValidationError:
                continue
            mutable_action = get_mutable_action(action.id)
            mutable_action.schema = updated_schema
            db.session.add(mutable_action)
            if action.type is not None and action.type.is_template:
                updated_template_action_ids.append(action.id)
    db.session.commit()
    for other_template_action_id in updated_template_action_ids:
        update_actions_using_template_action(other_template_action_id)


def get_action_type_ids_for_action_ids(
        action_ids: typing.Optional[typing.Sequence[int]]
) -> typing.Dict[int, typing.Optional[int]]:
    query = models.actions.Action.query.with_entities(
        models.actions.Action.id,
        models.actions.Action.type_id
    )
    if action_ids is not None:
        query = query.filter(
            models.actions.Action.id.in_(action_ids)
        )
    action_ids_and_action_type_ids = query.all()
    return {
        action_id: action_type_id
        for action_id, action_type_id in action_ids_and_action_type_ids
    }


def get_actions_for_topic(
        topic_id: int
) -> typing.List[Action]:
    """
    Get the list of actions assigned to a given topic.

    :param topic_id: the ID of an existing topic
    :return: the list of actions
    :raise errors.TopicDoesNotExistError: if the topic does not exist
    """
    actions = models.actions.Action.query.outerjoin(
        models.instruments.topic_instrument_association_table,
        models.Action.instrument_id == models.instruments.topic_instrument_association_table.c.instrument_id
    ).filter(
        db.or_(
            db.and_(
                models.Action.use_instrument_topics == db.false(),
                models.Action.topics.any(models.topics.Topic.id == topic_id)
            ),
            db.and_(
                models.Action.use_instrument_topics == db.true(),
                models.instruments.topic_instrument_association_table.c.topic_id == topic_id
            )
        )
    ).all()
    if not actions:
        topics.check_topic_exists(topic_id)
    return [
        Action.from_database(action)
        for action in actions
    ]


def sort_actions_for_user(
        actions: typing.Sequence[Action],
        user_id: int,
        sort_by_favorite: bool = True
) -> typing.List[Action]:
    """
    Sort an action list for a user.

    The actions are sorted by:
    - favorite / not favorite (if enabled)
    - action origin (local actions first)
    - user name (actions without users first)
    - instrument name (independent actions first)
    - action name

    :param actions: a list of actions to sort
    :param user_id: the ID of the user to sort actions for
    :param sort_by_favorite: whether favorite actions should be first in the sorted list
    :return: the sorted list of actions
    :raise errors.UserDoesNotExistError: if no user with the given user ID
        exists
    """
    if sort_by_favorite:
        user_favorite_action_ids = set(favorites.get_user_favorite_action_ids(user_id))
    else:
        user_favorite_action_ids = set()
    return sorted(actions, key=lambda action: (
        0 if action.id in user_favorite_action_ids else 1,
        0 if action.fed_id is None else 1,
        action.user.name.lower() if action.user and action.user.name is not None else '',
        get_translated_text(action.instrument.name).lower() if action.instrument else '',
        get_translated_text(action.name).lower()
    ))
