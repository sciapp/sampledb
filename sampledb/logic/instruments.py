# coding: utf-8
"""

"""

import typing

from .. import db
from ..models import Instrument
from . import users, errors


def create_instrument(name: str, description: str) -> Instrument:
    instrument = Instrument(
        name=name,
        description=description
    )
    db.session.add(instrument)
    db.session.commit()
    return instrument


def get_instruments() -> typing.List[Instrument]:
    return Instrument.query.all()


def get_instrument(instrument_id: int) -> Instrument:
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    return instrument


def update_instrument(instrument_id: int, name: str, description: str) -> Instrument:
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    instrument.name = name
    instrument.description = description
    db.session.add(instrument)
    db.session.commit()
    return instrument


def add_instrument_responsible_user(instrument_id: int, user_id: int):
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    user = users.get_user(user_id)
    instrument.responsible_users.append(user)
    db.session.add(instrument)
    db.session.commit()


def remove_instrument_responsible_user(instrument_id: int, user_id: int):
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    user = users.get_user(user_id)
    instrument.responsible_users.remove(user)
    db.session.add(instrument)
    db.session.commit()
