# coding: utf-8
"""

"""

import typing

from .. import db
from ..models import Action, ActionType
from . import errors, instruments, schemas


def create_action(action_type: ActionType, name: str, description: str, schema: dict, instrument_id: int=None) -> Action:
    schemas.validate_schema(schema)
    if instrument_id is not None:
        # ensure that the instrument can be found
        instruments.get_instrument(instrument_id)
    action = Action(
        action_type=action_type,
        name=name,
        description=description,
        schema=schema,
        instrument_id=instrument_id
    )
    db.session.add(action)
    db.session.commit()
    return action


def get_actions(action_type: ActionType=None) -> typing.List[Action]:
    if action_type:
        return Action.query.filter_by(type=action_type).all()
    return Action.query.all()


def get_action(action_id: int) -> Action:
    action = Action.query.get(action_id)
    if action is None:
        raise errors.ActionDoesNotExistError
    return action


def update_action(action_id: int, name: str, description: str, schema: dict) -> Action:
    schemas.validate_schema(schema)
    action = Action.query.get(action_id)
    if action is None:
        raise errors.ActionDoesNotExistError
    action.name = name
    action.description = description
    action.schema = schema
    db.session.add(action)
    db.session.commit()
    return action
