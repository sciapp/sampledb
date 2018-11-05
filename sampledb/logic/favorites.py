# coding: utf-8
"""
Logic for users' favorite actions and instruments.
"""

from typing import List

from .users import get_user
from .actions import get_action
from .instruments import get_instrument
from ..models import FavoriteAction, FavoriteInstrument
from .. import db


def add_favorite_action(action_id: int, user_id: int) -> None:
    """
    Add an action to the list of a user's favorite actions.

    :param action_id: the ID of an existing action
    :param user_id: the ID of an existing user
    :raises UserDoesNotExistError: if the action does not exist
    :raises ActionDoesNotExistError: if the user does not exist
    """
    user = get_user(user_id)
    action = get_action(action_id)
    db.session.add(FavoriteAction(action_id=action.id, user_id=user.id))
    db.session.commit()


def remove_favorite_action(action_id: int, user_id: int) -> None:
    """
    Remove an action from the list of a user's favorite actions.

    If the action is not a favorite, this function does nothing.

    :param action_id: the ID of an existing action
    :param user_id: the ID of an existing user
    :raises UserDoesNotExistError: if the action does not exist
    :raises ActionDoesNotExistError: if the user does not exist
    """
    user = get_user(user_id)
    action = get_action(action_id)
    favorite_action = FavoriteAction.query.filter_by(action_id=action.id, user_id=user.id).first()
    if favorite_action is not None:
        db.session.delete(favorite_action)
        db.session.commit()


def get_user_favorite_action_ids(user_id: int) -> List[int]:
    """
    Get a list of a user's favorite actions.

    :param user_id: the ID of an existing user
    :returns: a list of IDs of favorite actions
    :raises UserDoesNotExistError: if the action does not exist
    """
    user = get_user(user_id)
    favorite_actions = FavoriteAction.query.filter_by(user_id=user.id).all()
    return [
        favorite_action.action_id
        for favorite_action in favorite_actions
    ]


def add_favorite_instrument(instrument_id: int, user_id: int) -> None:
    """
    Add an instrument to the list of a user's favorite instruments.

    :param instrument_id: the ID of an existing instrument
    :param user_id: the ID of an existing user
    :raises UserDoesNotExistError: if the instrument does not exist
    :raises InstrumentDoesNotExistError: if the user does not exist
    """
    user = get_user(user_id)
    instrument = get_instrument(instrument_id)
    db.session.add(FavoriteInstrument(instrument_id=instrument.id, user_id=user.id))
    db.session.commit()


def remove_favorite_instrument(instrument_id: int, user_id: int) -> None:
    """
    Remove an instrument from the list of a user's favorite instruments.

    If the instrument is not a favorite, this function does nothing.

    :param instrument_id: the ID of an existing instrument
    :param user_id: the ID of an existing user
    :raises UserDoesNotExistError: if the instrument does not exist
    :raises InstrumentDoesNotExistError: if the user does not exist
    """
    user = get_user(user_id)
    instrument = get_instrument(instrument_id)
    favorite_instrument = FavoriteInstrument.query.filter_by(instrument_id=instrument.id, user_id=user.id).first()
    if favorite_instrument is not None:
        db.session.delete(favorite_instrument)
        db.session.commit()


def get_user_favorite_instrument_ids(user_id: int) -> List[int]:
    """
    Get a list of a user's favorite instruments.

    :param user_id: the ID of an existing user
    :returns: a list of IDs of favorite instruments
    :raises UserDoesNotExistError: if the instrument does not exist
    """
    user = get_user(user_id)
    favorite_instruments = FavoriteInstrument.query.filter_by(user_id=user.id).all()
    return [
        favorite_instrument.instrument_id
        for favorite_instrument in favorite_instruments
    ]
