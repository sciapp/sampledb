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
import collections
import typing

from .. import db
from .. import models
from ..models import SciCatExportType
from . import errors, instruments, users, schemas, components


class Action(collections.namedtuple('Action', [
    'id',
    'type_id',
    'type',
    'instrument_id',
    'instrument',
    'schema',
    'user_id',
    'user',
    'is_hidden',
    'name',
    'description',
    'description_is_markdown',
    'short_description',
    'short_description_is_markdown',
    'fed_id',
    'component_id',
    'component'
])):
    """
    This class provides an immutable wrapper around models.actions.Action.
    """

    def __new__(
            cls,
            id: int,
            type_id: int,
            type: typing.Optional['ActionType'],
            instrument_id: int,
            instrument: typing.Optional[instruments.Instrument],
            schema: typing.Dict[str, typing.Any],
            user_id: int,
            user: typing.Optional[users.User],
            is_hidden: bool,
            name: typing.Dict[str, str],
            description: typing.Dict[str, str],
            description_is_markdown: bool,
            short_description: typing.Dict[str, str],
            short_description_is_markdown: bool,
            fed_id: int,
            component_id: int,
            component: typing.Optional[components.Component]
    ):
        self = super(Action, cls).__new__(
            cls,
            id,
            type_id,
            type,
            instrument_id,
            instrument,
            schema,
            user_id,
            user,
            is_hidden,
            name,
            description,
            description_is_markdown,
            short_description,
            short_description_is_markdown,
            fed_id,
            component_id,
            component
        )
        return self

    @classmethod
    def from_database(cls, action: models.Action) -> 'Action':
        return Action(
            id=action.id,
            type_id=action.type_id,
            type=ActionType.from_database(action.type) if action.type is not None else None,
            instrument_id=action.instrument_id,
            instrument=action.instrument,  # TODO: instruments.Instrument.from_database(action.instrument)
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
            component=components.Component.from_database(action.component) if action.component is not None else None
        )

    def __repr__(self):
        return f"<{type(self).__name__}(id={self.id!r})>"


class ActionType(collections.namedtuple('ActionType', [
    'id',
    'name',
    'description',
    'object_name',
    'object_name_plural',
    'view_text',
    'perform_text',
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
    'enable_project_link',
    'disable_create_objects',
    'is_template',
    'fed_id',
    'component_id',
    'scicat_export_type'
])):
    """
    This class provides an immutable wrapper around models.actions.ActionType.
    """

    def __new__(
            cls,
            id: int,
            name: typing.Dict[str, str],
            description: typing.Dict[str, str],
            object_name: typing.Dict[str, str],
            object_name_plural: typing.Dict[str, str],
            view_text: typing.Dict[str, str],
            perform_text: typing.Dict[str, str],
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
            enable_project_link: bool,
            disable_create_objects: bool,
            is_template: bool,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None,
            scicat_export_type: typing.Optional[SciCatExportType] = None
    ):
        self = super(ActionType, cls).__new__(
            cls,
            id,
            name,
            description,
            object_name,
            object_name_plural,
            view_text,
            perform_text,
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
            enable_project_link,
            disable_create_objects,
            is_template,
            fed_id,
            component_id,
            scicat_export_type
        )
        return self

    @classmethod
    def from_database(cls, action_type: models.ActionType) -> 'ActionType':
        return ActionType(
            id=action_type.id,
            name=action_type.name,
            description=action_type.description,
            object_name=action_type.object_name,
            object_name_plural=action_type.object_name_plural,
            view_text=action_type.view_text,
            perform_text=action_type.perform_text,
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
            enable_project_link=action_type.enable_project_link,
            disable_create_objects=action_type.disable_create_objects,
            is_template=action_type.is_template,
            fed_id=action_type.fed_id,
            component_id=action_type.component_id,
            scicat_export_type=action_type.scicat_export_type
        )

    def __repr__(self):
        return f"<{type(self).__name__}(id={self.id!r})>"


def get_action_types(filter_fed_defaults: bool = False) -> typing.List[ActionType]:
    """
    Return the list of all existing action types.

    :return: the action types
    """
    if filter_fed_defaults:
        return [
            ActionType.from_database(action_type)
            for action_type in models.ActionType.query.filter(db.or_(models.ActionType.fed_id > 0, models.ActionType.fed_id.is_(None))).order_by(models.ActionType.id).all()
        ]
    else:
        return [
            ActionType.from_database(action_type)
            for action_type in models.ActionType.query.order_by(models.ActionType.id).all()
        ]


def get_action_type(action_type_id: int, component_id: typing.Optional[int] = None) -> ActionType:
    """
    Returns the action type with the given action type ID.

    :param action_type_id: the ID of an existing action type
    :return: the action type
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    if component_id is None:
        action_type = models.ActionType.query.get(action_type_id)
    else:
        # ensure that the component can be found
        components.get_component(component_id)
        action_type = models.ActionType.query.filter_by(fed_id=action_type_id, component_id=component_id).first()
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
        enable_project_link: bool,
        disable_create_objects: bool,
        is_template: bool,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None,
        scicat_export_type: typing.Optional[SciCatExportType] = None
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
    :param scicat_export_type: the SciCat type to use during export, or None
    :return: the created action type
    """
    if (component_id is None) != (fed_id is None):
        raise TypeError('Invalid parameter combination.')

    if component_id is not None:
        # ensure that the component can be found
        components.get_component(component_id)

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
        enable_project_link=enable_project_link,
        disable_create_objects=disable_create_objects,
        is_template=is_template,
        fed_id=fed_id,
        component_id=component_id,
        scicat_export_type=scicat_export_type
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
        enable_project_link: bool,
        disable_create_objects: bool,
        is_template: bool,
        scicat_export_type: typing.Optional[SciCatExportType] = None
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
    :param scicat_export_type: the SciCat type to use during export, or None
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
    action_type.disable_create_objects = disable_create_objects
    action_type.is_template = is_template
    action_type.scicat_export_type = scicat_export_type
    db.session.add(action_type)
    db.session.commit()
    return ActionType.from_database(action_type)


def create_action(
        *,
        action_type_id: typing.Optional[int],
        schema: typing.Optional[dict],
        instrument_id: typing.Optional[int] = None,
        user_id: typing.Optional[int] = None,
        description_is_markdown: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None
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
    :param fed_id: the ID of the related action at the exporting component
    :param component_id: the ID of the exporting component
    :return: the created action
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    :raise errors.SchemaValidationError: when the schema is invalid
    :raise errors.InstrumentDoesNotExistError: when instrument_id is not None
        and no instrument with the given instrument ID exists
    :raise errors.UserDoesNotExistError: when user_id is not None and no user
        with the given user ID exists
    """
    if (component_id is None) != (fed_id is None) or (component_id is None and (action_type_id is None or schema is None)):
        raise TypeError('Invalid parameter combination.')

    if action_type_id is not None:
        # ensure the action type exists
        get_action_type(action_type_id)

    if schema is not None:
        schemas.validate_schema(schema, strict=True)
    if instrument_id is not None:
        # ensure that the instrument can be found
        instruments.get_instrument(instrument_id)
    if user_id is not None:
        # ensure that the user can be found
        users.get_user(user_id)

    if component_id is not None:
        # ensure that the component can be found
        components.get_component(component_id)

    action = models.Action(
        action_type_id=action_type_id,
        description_is_markdown=description_is_markdown,
        is_hidden=is_hidden,
        schema=schema,
        instrument_id=instrument_id,
        user_id=user_id,
        short_description_is_markdown=short_description_is_markdown,
        fed_id=fed_id,
        component_id=component_id
    )
    db.session.add(action)
    db.session.commit()
    return Action.from_database(action)


def get_actions(action_type_id: typing.Optional[int] = None) -> typing.List[Action]:
    """
    Returns all actions, optionally only actions of a given type.

    :param action_type_id: None or the ID of an existing action type
    :return: the list of actions
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    if action_type_id is not None:
        actions = models.Action.query.filter_by(type_id=action_type_id).all()
        if not actions:
            # ensure the action type exists
            get_action_type(action_type_id=action_type_id)
    else:
        actions = models.Action.query.all()
    return [
        Action.from_database(action)
        for action in actions
    ]


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
    if component_id is None:
        action = models.Action.query.get(action_id)
    else:
        # ensure that the component can be found
        components.get_component(component_id)
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
    :param is_hidden: None or whether the action should be hidden
    :param short_description_is_markdown: whether the short description
        contains Markdown
    :raise errors.SchemaValidationError: when the schema is invalid
    :raise errors.InstrumentDoesNotExistError: when instrument_id is not None
        and no instrument with the given instrument ID exists
    """
    schemas.validate_schema(schema, invalid_template_action_ids=[action_id], strict=True)
    action = get_mutable_action(action_id)
    action.description_is_markdown = description_is_markdown
    action.schema = schema
    action.short_description_is_markdown = short_description_is_markdown
    if is_hidden is not None:
        action.is_hidden = is_hidden
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
            if action.type.is_template:
                updated_template_action_ids.append(action.id)
    db.session.commit()
    for other_template_action_id in updated_template_action_ids:
        update_actions_using_template_action(other_template_action_id)
