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


def create_instrument(
        *,
        description_is_markdown: bool = False,
        users_can_create_log_entries: bool = False,
        users_can_view_log_entries: bool = False,
        notes_is_markdown: bool = False,
        create_log_entry_default: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False
) -> Instrument:
    """
    Creates a new instrument.

    :param description_is_markdown: whether the description contains Markdown
    :param users_can_create_log_entries: whether or not users can create log
        entries for this instrument
    :param users_can_view_log_entries: whether or not users can view the log
        entries for this instrument
    :param notes_is_markdown: whether the notes contain Markdown
    :param create_log_entry_default: the default for whether or not a log
        entry should be created during object creation by instrument scientists
    :param is_hidden: whether or not this instrument is hidden
    :param short_description_is_markdown: whether the short description
        contains Markdown
    :return: the new instrument
    """
    instrument = Instrument(
        description_is_markdown=description_is_markdown,
        users_can_create_log_entries=users_can_create_log_entries,
        users_can_view_log_entries=users_can_view_log_entries,
        notes_is_markdown=notes_is_markdown,
        create_log_entry_default=create_log_entry_default,
        is_hidden=is_hidden,
        short_description_is_markdown=short_description_is_markdown
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


def update_instrument(
        *,
        instrument_id: int,
        description_is_markdown: typing.Optional[bool] = None,
        users_can_create_log_entries: typing.Optional[bool] = None,
        users_can_view_log_entries: typing.Optional[bool] = None,
        notes_is_markdown: typing.Optional[bool] = None,
        create_log_entry_default: typing.Optional[bool] = None,
        is_hidden: typing.Optional[bool] = None,
        short_description_is_markdown: typing.Optional[bool] = None
) -> None:
    """
    Updates the instrument.

    :param instrument_id: the ID of an existing instrument
    :param description_is_markdown: whether the description contains Markdown,
        or None
    :param users_can_create_log_entries: whether or not users can create log
        entries for this instrument, or None
    :param users_can_view_log_entries: whether or not users can view the log
        entries for this instrument, or None
    :param notes_is_markdown: whether the notes contain Markdown, or None
    :param create_log_entry_default: the default for whether or not a log
        entry should be created during object creation by instrument
        scientists, or None
    :param is_hidden: whether or not this instrument is hidden, or None
    :param short_description_is_markdown: whether the short description
        contains Markdown, or None
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    instrument = Instrument.query.get(instrument_id)
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    if description_is_markdown is not None:
        instrument.description_is_markdown = description_is_markdown
    if users_can_create_log_entries is not None:
        instrument.users_can_create_log_entries = users_can_create_log_entries
    if users_can_view_log_entries is not None:
        instrument.users_can_view_log_entries = users_can_view_log_entries
    if notes_is_markdown is not None:
        instrument.notes_is_markdown = notes_is_markdown
    if create_log_entry_default is not None:
        instrument.create_log_entry_default = create_log_entry_default
    if short_description_is_markdown is not None:
        instrument.short_description_is_markdown = short_description_is_markdown
    if is_hidden is not None:
        instrument.is_hidden = is_hidden
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


def get_user_instruments(user_id: int, exclude_hidden: bool = False) -> typing.List[int]:
    """
    Get a list of instruments a user with a given user ID is responsible for.

    :param user_id: the ID of an existing user
    :param exclude_hidden: whether hidden instruments should be excluded
    :return: a list of instrument IDs
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure that the user exists
    users.get_user(user_id)
    instrument_id_query = db.session.query(instrument_user_association_table.c.instrument_id).filter(instrument_user_association_table.c.user_id == user_id)
    if exclude_hidden:
        instrument_id_query = instrument_id_query.join(
            Instrument,
            instrument_user_association_table.c.instrument_id == Instrument.id
        ).filter(Instrument.is_hidden == db.false())
    instrument_ids = [
        instrument_user_association[0]
        for instrument_user_association in instrument_id_query.order_by(instrument_user_association_table.c.instrument_id).all()
    ]
    return instrument_ids
