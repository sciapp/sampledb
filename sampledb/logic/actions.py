# coding: utf-8
"""
Logic module for management of actions

Actions are used to represent all kinds of methods or processes that result
in the creation of a new sample or measurement. What kind of object is
created when performing an action is defined by the action's ActionType.
The action's schema defines what information should or may be recorded in
iffSamples for a newly created object.

Actions can be related to an instrument, which serves both to group actions
together and to provide instrument responsible users with permissions for
samples or measurements created with their instrument.

Actions can also be user-defined, to allow advanced users to create actions
for instruments which would otherwise not be included.

As actions form the basis for objects, they cannot be deleted. However, an
action can be altered as long as the type and instrument stay the same.
"""

import typing

from .. import db
from ..models import Action, ActionType
from . import errors, instruments, users, schemas


def create_action(
        action_type: ActionType,
        name: str,
        description: str,
        schema: dict,
        instrument_id: typing.Optional[int] = None,
        user_id: typing.Optional[int] = None,
        description_as_html: typing.Optional[str] = None,
        is_hidden: bool = False
) -> Action:
    """
    Creates a new action with the given type, name, description and schema. If
    instrument_id is not None, the action will belong to the instrument with
    this ID.

    :param action_type: the type of the action
    :param name: the name of the action
    :param description: a (possibly empty) description for the action
    :param schema: the schema for objects created using this action
    :param instrument_id: None or the ID of an existing instrument
    :param user_id: None or the ID of an existing user
    :param description_as_html: None or the description as HTML
    :param is_hidden: None or whether or not the action should be hidden
    :return: the created action
    :raise errors.SchemaValidationError: when the schema is invalid
    :raise errors.InstrumentDoesNotExistError: when instrument_id is not None
        and no instrument with the given instrument ID exists
    :raise errors.UserDoesNotExistError: when user_id is not None and no user
        with the given user ID exists
    """
    schemas.validate_schema(schema)
    if instrument_id is not None:
        # ensure that the instrument can be found
        instruments.get_instrument(instrument_id)
    if user_id is not None:
        # ensure that the user can be found
        users.get_user(user_id)

    action = Action(
        action_type=action_type,
        name=name,
        description=description,
        description_as_html=description_as_html,
        is_hidden=is_hidden,
        schema=schema,
        instrument_id=instrument_id,
        user_id=user_id
    )
    db.session.add(action)
    db.session.commit()
    return action


def get_actions(action_type: typing.Optional[ActionType] = None) -> typing.List[Action]:
    """
    Returns all actions, optionally only actions of a given type.

    :param action_type: None or the type of actions' that should be returned
    :return: the list of actions
    """
    if action_type is not None:
        return Action.query.filter_by(type=action_type).all()
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
        action_id: int,
        name: str,
        description: str,
        schema: dict,
        description_as_html: typing.Optional[str] = None,
        is_hidden: typing.Optional[bool] = None
) -> None:
    """
    Updates the action with the given action ID, setting its name, description and schema.

    :param action_id: the ID of an existing action
    :param name: the new name of the action
    :param description: the new (possibly empty) description of the action
    :param schema: the new schema for objects created using this action
    :param description_as_html: None or the description as HTML
    :param is_hidden: None or whether or not the action should be hidden
    :raise errors.SchemaValidationError: when the schema is invalid
    :raise errors.InstrumentDoesNotExistError: when instrument_id is not None
        and no instrument with the given instrument ID exists
    """
    schemas.validate_schema(schema)
    action = Action.query.get(action_id)
    if action is None:
        raise errors.ActionDoesNotExistError()
    action.name = name
    action.description = description
    action.description_as_html = description_as_html
    action.schema = schema
    if is_hidden is not None:
        action.is_hidden = is_hidden
    db.session.add(action)
    db.session.commit()
