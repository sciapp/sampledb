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
from . import users, errors


def create_instrument(name: str, description: str) -> Instrument:
    """
    Creates a new instrument with the given name and description.

    :param name: the name of the instrument
    :param description: a (possibly empty) description of the instrument
    :return: the new instrument
    """
    instrument = Instrument(
        name=name,
        description=description
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


def update_instrument(instrument_id: int, name: str, description: str) -> None:
    """
    Updates the instrument name and description.

    :param instrument_id: the ID of an existing instrument
    :param name: the new name of the instrument
    :param description: the new (possibly empty) description of the instrument
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    instrument.name = name
    instrument.description = description
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
