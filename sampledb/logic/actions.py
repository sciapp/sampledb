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

import collections
import typing

from .. import db
from .. import models
from ..models import Action
from . import errors, instruments, users, schemas


class ActionType(collections.namedtuple('ActionType', [
    'id',
    'admin_only',
    'show_on_frontpage',
    'show_in_navbar',
    'enable_labels',
    'enable_files',
    'enable_locations',
    'enable_publications',
    'enable_comments',
    'enable_activity_log',
    'enable_related_objects',
    'enable_project_link'
])):
    """
    This class provides an immutable wrapper around models.actions.ActionType.
    """

    def __new__(
            cls,
            id: int,
            admin_only: bool,
            show_on_frontpage: bool,
            show_in_navbar: bool,
            enable_labels: bool,
            enable_files: bool,
            enable_locations: bool,
            enable_publications: bool,
            enable_comments: bool,
            enable_activity_log: bool,
            enable_related_objects: bool,
            enable_project_link: bool
    ):
        self = super(ActionType, cls).__new__(
            cls,
            id,
            admin_only,
            show_on_frontpage,
            show_in_navbar,
            enable_labels,
            enable_files,
            enable_locations,
            enable_publications,
            enable_comments,
            enable_activity_log,
            enable_related_objects,
            enable_project_link
        )
        return self

    @classmethod
    def from_database(cls, action_type: models.ActionType) -> 'ActionType':
        return ActionType(
            id=action_type.id,
            admin_only=action_type.admin_only,
            show_on_frontpage=action_type.show_on_frontpage,
            show_in_navbar=action_type.show_in_navbar,
            enable_labels=action_type.enable_labels,
            enable_files=action_type.enable_files,
            enable_locations=action_type.enable_locations,
            enable_publications=action_type.enable_publications,
            enable_comments=action_type.enable_comments,
            enable_activity_log=action_type.enable_activity_log,
            enable_related_objects=action_type.enable_related_objects,
            enable_project_link=action_type.enable_project_link
        )

    def __repr__(self):
        return f"<{type(self).__name__}(id={self.id!r})>"


def get_action_types() -> typing.List[ActionType]:
    """
    Return the list of all existing action types.

    :return: the action types
    """
    return [
        ActionType.from_database(action_type)
        for action_type in models.ActionType.query.order_by(models.ActionType.id).all()
    ]


def get_action_type(action_type_id: int) -> ActionType:
    """
    Returns the action type with the given action type ID.

    :param action_type_id: the ID of an existing action type
    :return: the action type
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    action_type = models.ActionType.query.get(action_type_id)
    if action_type is None:
        raise errors.ActionTypeDoesNotExistError()
    return ActionType.from_database(action_type)


def create_action_type(
        admin_only: bool,
        show_on_frontpage: bool,
        show_in_navbar: bool,
        enable_labels: bool,
        enable_files: bool,
        enable_locations: bool,
        enable_publications: bool,
        enable_comments: bool,
        enable_activity_log: bool,
        enable_related_objects: bool,
        enable_project_link: bool
) -> ActionType:
    """
    Create a new action type.

    :param admin_only: whether actions of this type can only be created by administrators
    :param show_on_frontpage: whether this action type should be shown on the frontpage
    :param show_in_navbar: whether actions of this type should be shown in the navbar
    :param enable_labels: whether labels should be enabled for actions of this type
    :param enable_files: whether file uploads should be enabled for actions of this type
    :param enable_locations: whether locations and responsible users should be enabled for actions of this type
    :param enable_publications: whether publications should be enabled for actions of this type
    :param enable_comments: whether comments should be enabled for actions of this type
    :param enable_activity_log: whether the activity log should be enabled for actions of this type
    :param enable_related_objects: whether showing related objects should be enabled for actions of this type
    :param enable_project_link: objects created with actions of this type can be linked to a project group
    :return: the created action type
    """
    action_type = models.ActionType(
        admin_only=admin_only,
        show_on_frontpage=show_on_frontpage,
        show_in_navbar=show_in_navbar,
        enable_labels=enable_labels,
        enable_files=enable_files,
        enable_locations=enable_locations,
        enable_publications=enable_publications,
        enable_comments=enable_comments,
        enable_activity_log=enable_activity_log,
        enable_related_objects=enable_related_objects,
        enable_project_link=enable_project_link
    )
    db.session.add(action_type)
    db.session.commit()
    return ActionType.from_database(action_type)


def update_action_type(
        action_type_id: int,
        admin_only: bool,
        show_on_frontpage: bool,
        show_in_navbar: bool,
        enable_labels: bool,
        enable_files: bool,
        enable_locations: bool,
        enable_publications: bool,
        enable_comments: bool,
        enable_activity_log: bool,
        enable_related_objects: bool,
        enable_project_link: bool
) -> ActionType:
    """
    Update an existing action type.

    :param action_type_id: the ID of an existing action type
    :param admin_only: whether actions of this type can only be created by administrators
    :param show_on_frontpage: whether this action type should be shown on the frontpage
    :param show_in_navbar: whether actions of this type should be shown in the navbar
    :param enable_labels: whether labels should be enabled for actions of this type
    :param enable_files: whether file uploads should be enabled for actions of this type
    :param enable_locations: whether locations and responsible users should be enabled for actions of this type
    :param enable_publications: whether publications should be enabled for actions of this type
    :param enable_comments: whether comments should be enabled for actions of this type
    :param enable_activity_log: whether the activity log should be enabled for actions of this type
    :param enable_related_objects: whether showing related objects should be enabled for actions of this type
    :param enable_project_link: objects created with actions of this type can be linked to a project group
    :return: the created action type
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    action_type = models.ActionType.query.get(action_type_id)
    if action_type is None:
        raise errors.ActionTypeDoesNotExistError()
    action_type.admin_only = admin_only
    action_type.show_on_frontpage = show_on_frontpage
    action_type.show_in_navbar = show_in_navbar
    action_type.enable_labels = enable_labels
    action_type.enable_files = enable_files
    action_type.enable_locations = enable_locations
    action_type.enable_publications = enable_publications
    action_type.enable_comments = enable_comments
    action_type.enable_activity_log = enable_activity_log
    action_type.enable_related_objects = enable_related_objects
    action_type.enable_project_link = enable_project_link
    db.session.add(action_type)
    db.session.commit()
    return ActionType.from_database(action_type)


def create_action(
        *,
        action_type_id: int,
        schema: dict,
        instrument_id: typing.Optional[int] = None,
        user_id: typing.Optional[int] = None,
        description_is_markdown: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False
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
    :param is_hidden: None or whether or not the action should be hidden
    :param short_description_is_markdown: whether the short description
        contains Markdown
    :return: the created action
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    :raise errors.SchemaValidationError: when the schema is invalid
    :raise errors.InstrumentDoesNotExistError: when instrument_id is not None
        and no instrument with the given instrument ID exists
    :raise errors.UserDoesNotExistError: when user_id is not None and no user
        with the given user ID exists
    """
    # ensure the action type exists
    get_action_type(action_type_id)

    schemas.validate_schema(schema)
    if instrument_id is not None:
        # ensure that the instrument can be found
        instruments.get_instrument(instrument_id)
    if user_id is not None:
        # ensure that the user can be found
        users.get_user(user_id)

    action = Action(
        action_type_id=action_type_id,
        description_is_markdown=description_is_markdown,
        is_hidden=is_hidden,
        schema=schema,
        instrument_id=instrument_id,
        user_id=user_id,
        short_description_is_markdown=short_description_is_markdown
    )
    db.session.add(action)
    db.session.commit()
    return action


def get_actions(action_type_id: typing.Optional[int] = None) -> typing.List[Action]:
    """
    Returns all actions, optionally only actions of a given type.

    :param action_type_id: None or the ID of an existing action type
    :return: the list of actions
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    if action_type_id is not None:
        actions = Action.query.filter_by(type_id=action_type_id).all()
        if not actions:
            # ensure the action type exists
            get_action_type(action_type_id=action_type_id)
        return actions
    return Action.query.all()


def get_action(action_id: int) -> Action:
    """
    Returns the action with the given action ID.

    :param action_id: the ID of an existing action
    :return: the action
    :raise errors.ActionDoesNotExistError: when no action with the given
        action ID exists
    """
    action = Action.query.get(action_id)
    if action is None:
        raise errors.ActionDoesNotExistError()
    return action


def update_action(
        *,
        action_id: int,
        schema: dict,
        description_is_markdown: bool = False,
        is_hidden: typing.Optional[bool] = None,
        short_description_is_markdown: bool = False
) -> None:
    """
    Updates the action with the given action ID, setting its schema.

    :param action_id: the ID of an existing action
    :param schema: the new schema for objects created using this action
    :param description_is_markdown: whether the description contains Markdown
    :param is_hidden: None or whether or not the action should be hidden
    :param short_description_is_markdown: whether the short description
        contains Markdown
    :raise errors.SchemaValidationError: when the schema is invalid
    :raise errors.InstrumentDoesNotExistError: when instrument_id is not None
        and no instrument with the given instrument ID exists
    """
    schemas.validate_schema(schema)
    action = Action.query.get(action_id)
    if action is None:
        raise errors.ActionDoesNotExistError()
    action.description_is_markdown = description_is_markdown
    action.schema = schema
    action.short_description_is_markdown = short_description_is_markdown
    if is_hidden is not None:
        action.is_hidden = is_hidden
    db.session.add(action)
    db.session.commit()
