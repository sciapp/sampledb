# coding: utf-8
"""
Logic module for management of instruments

Instruments are used to group actions together and provide instrument
responsible users with permissions for samples or measurements produced
using the instrument.

Similar to actions, instruments cannot be deleted. However, all information
about an instrument may be altered.
"""

import typing

from .. import db
from ..models import Instrument
from ..models.instruments import instrument_user_association_table
from . import users, errors


def create_instrument(name: str, description: str, description_as_html: typing.Optional[str] = None) -> Instrument:
    """
    Creates a new instrument with the given name and description.

    :param name: the name of the instrument
    :param description: a (possibly empty) description of the instrument
    :param description_as_html: None or the description as HTML
    :return: the new instrument
    """
    instrument = Instrument(
        name=name,
        description=description,
        description_as_html=description_as_html
    )
    db.session.add(instrument)
    db.session.commit()
    return instrument


def get_instruments() -> typing.List[Instrument]:
    """
    Returns all instruments.

    :return: the list of instruments
    """
    return Instrument.query.all()


def get_instrument(instrument_id: int) -> Instrument:
    """
    Returns the instrument with the given instrument ID.

    :param instrument_id: the ID of an existing instrument
    :return: the instrument
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    return instrument


def update_instrument(instrument_id: int, name: str, description: str, description_as_html: typing.Optional[str] = None) -> None:
    """
    Updates the instrument name and description.

    :param instrument_id: the ID of an existing instrument
    :param name: the new name of the instrument
    :param description: the new (possibly empty) description of the instrument
    :param description_as_html: None or the description as HTML
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    instrument.name = name
    instrument.description = description
    instrument.description_as_html = description_as_html
    db.session.add(instrument)
    db.session.commit()


def add_instrument_responsible_user(instrument_id: int, user_id: int) -> None:
    """
    Adds the user with the given user ID to the list of instrument responsible
    users.

    :param instrument_id: the ID of an existing instrument
    :param user_id: the ID of an existing user
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.UserAlreadyResponsibleForInstrumentError: when the user is
        already responsible for the instrument
    """
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    user = users.get_user(user_id)
    if user in instrument.responsible_users:
        raise errors.UserAlreadyResponsibleForInstrumentError()
    instrument.responsible_users.append(user)
    db.session.add(instrument)
    db.session.commit()


def remove_instrument_responsible_user(instrument_id: int, user_id: int) -> None:
    """
    Removes the user with the given user ID from the list of instrument
    responsible users.

    :param instrument_id: the ID of an existing instrument
    :param user_id: the ID of an existing user
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.UserNotResponsibleForInstrumentError: when the user is not
        responsible for the instrument
    """
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    user = users.get_user(user_id)
    if user not in instrument.responsible_users:
        raise errors.UserNotResponsibleForInstrumentError()
    instrument.responsible_users.remove(user)
    db.session.add(instrument)
    db.session.commit()


def set_instrument_responsible_users(instrument_id: int, user_ids: typing.List[int]) -> None:
    """
    Set the list of instrument responsible users for a an instrument.

    :param instrument_id: the ID of an existing instrument
    :param user_ids: the IDs of existing users
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    :raise errors.UserDoesNotExistError: when no user with one of the given
        user IDs exists
    """
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    instrument.responsible_users.clear()
    for user_id in user_ids:
        user = users.get_user(user_id)
        instrument.responsible_users.append(user)
    db.session.add(instrument)
    db.session.commit()


def get_user_instruments(user_id: int) -> typing.List[int]:
    """
    Get a list of instruments a user with a given user ID is responsible for.

    :param user_id: the ID of an existing user
    :return: a list of instrument IDs
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure that the user exists
    users.get_user(user_id)
    instrument_ids = [
        instrument_user_association[0]
        for instrument_user_association in db.session.query(instrument_user_association_table.c.instrument_id).filter(instrument_user_association_table.c.user_id == user_id).order_by(instrument_user_association_table.c.instrument_id).all()
    ]
    return instrument_ids
