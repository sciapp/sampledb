# coding: utf-8
"""
Logic module for management of instruments

Instruments are used to group actions together and provide instrument
responsible users with permissions for samples or measurements produced
using the instrument.

Similar to actions, instruments cannot be deleted. However, all information
about an instrument may be altered.
"""

import dataclasses
import typing

from .components import check_component_exists
from .. import db
from .. import models
from ..models.instruments import instrument_user_association_table
from . import users, errors, components, locations, objects, topics
from .utils import cache


@dataclasses.dataclass(frozen=True)
class Instrument:
    """
    This class provides an immutable wrapper around models.instruments.Instrument.
    """
    id: int
    responsible_users: typing.List[users.User]
    users_can_create_log_entries: bool
    users_can_view_log_entries: bool
    create_log_entry_default: bool
    is_hidden: bool
    name: typing.Dict[str, str]
    notes: typing.Dict[str, str]
    notes_is_markdown: bool
    description: typing.Dict[str, str]
    description_is_markdown: bool
    short_description: typing.Dict[str, str]
    short_description_is_markdown: bool
    fed_id: typing.Optional[int]
    component_id: typing.Optional[int]
    component: typing.Optional[components.Component]
    location_id: typing.Optional[int]
    location: typing.Optional[locations.Location]
    object_id: typing.Optional[int]
    show_linked_object_data: bool
    topics: typing.List[topics.Topic]

    @classmethod
    def from_database(cls, instrument: models.Instrument) -> 'Instrument':
        return Instrument(
            id=instrument.id,
            responsible_users=[
                users.User.from_database(user)
                for user in instrument.responsible_users
            ],
            users_can_create_log_entries=instrument.users_can_create_log_entries,
            users_can_view_log_entries=instrument.users_can_view_log_entries,
            create_log_entry_default=instrument.create_log_entry_default,
            is_hidden=instrument.is_hidden,
            name=instrument.name,
            notes=instrument.notes,
            notes_is_markdown=bool(instrument.notes_is_markdown),
            description=instrument.description,
            description_is_markdown=bool(instrument.description_is_markdown),
            short_description=instrument.short_description,
            short_description_is_markdown=bool(instrument.short_description_is_markdown),
            fed_id=instrument.fed_id,
            component_id=instrument.component_id,
            component=components.Component.from_database(instrument.component) if instrument.component is not None else None,
            location_id=instrument.location_id,
            location=locations.Location.from_database(instrument.location) if instrument.location is not None else None,
            object_id=instrument.object_id,
            show_linked_object_data=instrument.show_linked_object_data,
            topics=[topics.Topic.from_database(topic) for topic in instrument.topics],
        )

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(id={self.id!r})>"


@typing.overload
def create_instrument(
        *,
        description_is_markdown: bool = False,
        users_can_create_log_entries: bool = False,
        users_can_view_log_entries: bool = False,
        notes_is_markdown: bool = False,
        create_log_entry_default: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False,
        fed_id: None = None,
        component_id: None = None,
        show_linked_object_data: bool = True,
) -> Instrument:
    ...


@typing.overload
def create_instrument(
        *,
        description_is_markdown: bool = False,
        users_can_create_log_entries: bool = False,
        users_can_view_log_entries: bool = False,
        notes_is_markdown: bool = False,
        create_log_entry_default: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False,
        fed_id: int,
        component_id: int,
        show_linked_object_data: bool = True,
) -> Instrument:
    ...


def create_instrument(
        *,
        description_is_markdown: bool = False,
        users_can_create_log_entries: bool = False,
        users_can_view_log_entries: bool = False,
        notes_is_markdown: bool = False,
        create_log_entry_default: bool = False,
        is_hidden: bool = False,
        short_description_is_markdown: bool = False,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None,
        show_linked_object_data: bool = True,
) -> Instrument:
    """
    Creates a new instrument.

    :param description_is_markdown: whether the description contains Markdown
    :param users_can_create_log_entries: whether users can create log
        entries for this instrument
    :param users_can_view_log_entries: whether users can view the log
        entries for this instrument
    :param notes_is_markdown: whether the notes contain Markdown
    :param create_log_entry_default: the default for whether a log
        entry should be created during object creation by instrument scientists
    :param is_hidden: whether this instrument is hidden
    :param short_description_is_markdown: whether the short description
        contains Markdown
    :param fed_id: the ID of the related instrument at the exporting component
    :param component_id: the ID of the exporting component
    :param show_linked_object_data: whether the data for a linked object
        should be shown
    :return: the new instrument
    """
    assert (component_id is None) == (fed_id is None)

    if component_id is not None:
        check_component_exists(component_id)

    instrument = models.Instrument(
        description_is_markdown=description_is_markdown,
        users_can_create_log_entries=users_can_create_log_entries,
        users_can_view_log_entries=users_can_view_log_entries,
        notes_is_markdown=notes_is_markdown,
        create_log_entry_default=create_log_entry_default,
        is_hidden=is_hidden,
        short_description_is_markdown=short_description_is_markdown,
        fed_id=fed_id,
        component_id=component_id,
        show_linked_object_data=show_linked_object_data,
    )
    db.session.add(instrument)
    db.session.commit()
    return Instrument.from_database(instrument)


def get_instruments() -> typing.List[Instrument]:
    """
    Returns all instruments.

    :return: the list of instruments
    """
    return [
        Instrument.from_database(instrument)
        for instrument in models.Instrument.query.all()
    ]


@cache
def check_instrument_exists(
        instrument_id: int
) -> None:
    """
    Check whether an instrument with the given instrument ID exists.

    :param instrument_id: the ID of an existing instrument
    :raise errors.InstrumentDoesNotExistError: when no instrument with the given
        instrument ID exists
    """
    if not db.session.query(db.exists().where(models.Instrument.id == instrument_id)).scalar():
        raise errors.InstrumentDoesNotExistError()


def get_mutable_instrument(
        instrument_id: int,
        component_id: typing.Optional[int] = None
) -> models.Instrument:
    """
    Get the mutable instrument instance to perform changes in the database on.

    :param instrument_id: the ID of an existing instrument
    :param component_id: the ID of an existing component, or None
    :return: the instrument
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    instrument: typing.Optional[models.Instrument]
    if component_id is None:
        instrument = models.Instrument.query.filter_by(id=instrument_id).first()
    else:
        instrument = models.Instrument.query.filter_by(fed_id=instrument_id, component_id=component_id).first()
    if instrument is None:
        if component_id is not None:
            check_component_exists(component_id)
        raise errors.InstrumentDoesNotExistError()
    return instrument


def get_instrument(
        instrument_id: int,
        component_id: typing.Optional[int] = None
) -> Instrument:
    """
    Return the instrument with the given instrument ID.

    :param instrument_id: the ID of an existing instrument
    :param component_id: the ID of an existing component, or None
    :return: the instrument
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    return Instrument.from_database(get_mutable_instrument(instrument_id, component_id))


def update_instrument(
        *,
        instrument_id: int,
        description_is_markdown: typing.Optional[bool] = None,
        users_can_create_log_entries: typing.Optional[bool] = None,
        users_can_view_log_entries: typing.Optional[bool] = None,
        notes_is_markdown: typing.Optional[bool] = None,
        create_log_entry_default: typing.Optional[bool] = None,
        is_hidden: typing.Optional[bool] = None,
        short_description_is_markdown: typing.Optional[bool] = None,
        show_linked_object_data: typing.Optional[bool] = None
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
    :param show_linked_object_data: whether the data for a linked object
        should be shown, or None
    :param short_description_is_markdown: whether the short description
        contains Markdown, or None
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    instrument = models.Instrument.query.filter_by(id=instrument_id).first()
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
    if show_linked_object_data is not None:
        instrument.show_linked_object_data = show_linked_object_data
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
    instrument = models.Instrument.query.filter_by(id=instrument_id).first()
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    user = users.get_mutable_user(user_id)
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
    instrument = models.Instrument.query.filter_by(id=instrument_id).first()
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    user = users.get_mutable_user(user_id)
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
    instrument = models.Instrument.query.filter_by(id=instrument_id).first()
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    instrument.responsible_users.clear()
    for user_id in user_ids:
        user = users.get_mutable_user(user_id)
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
    users.check_user_exists(user_id)
    instrument_id_query = db.session.query(
        instrument_user_association_table.c.instrument_id
    ).filter(instrument_user_association_table.c.user_id == user_id)
    if exclude_hidden:
        instrument_id_query = instrument_id_query.join(
            models.Instrument,
            instrument_user_association_table.c.instrument_id == models.Instrument.id
        ).filter(models.Instrument.is_hidden == db.false())
    instrument_ids = [
        instrument_user_association[0]
        for instrument_user_association in instrument_id_query.order_by(instrument_user_association_table.c.instrument_id).all()
    ]
    return instrument_ids


def set_instrument_location(instrument_id: int, location_id: typing.Optional[int]) -> None:
    """
    Set the location of an instrument.

    :param instrument_id: the ID of an existing instrument
    :param location_id: the ID of an existing location
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    :raise errors.LocationDoesNotExistError: when no location with the
        given location ID exists
    """
    if location_id is not None:
        # ensure the location exists
        locations.check_location_exists(location_id)
    instrument = models.Instrument.query.filter_by(id=instrument_id).first()
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    instrument.location_id = location_id
    db.session.add(instrument)
    db.session.commit()


def set_instrument_object(instrument_id: int, object_id: typing.Optional[int]) -> None:
    """
    Set the object containing the metadata for an instrument.

    :param instrument_id: the ID of an existing instrument
    :param object_id: the ID of an existing object, or None
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    :raise errors.ObjectDoesNotExistError: when no object with the
        given object ID exists
    :raise errors.InstrumentObjectLinkAlreadyExistsError: if the object is
        already linked to an instrument or the instrument is already linked to
        an object
    """
    if object_id is not None:
        # ensure the object exists
        objects.check_object_exists(object_id)
    instrument = models.Instrument.query.filter_by(id=instrument_id).first()
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    if object_id is not None:
        if instrument.object_id is not None:
            raise errors.InstrumentObjectLinkAlreadyExistsError()
        linked_instrument = models.Instrument.query.filter_by(object_id=object_id).first()
        if linked_instrument is not None:
            raise errors.InstrumentObjectLinkAlreadyExistsError()
    instrument.object_id = object_id
    db.session.add(instrument)
    db.session.commit()


def get_instrument_object_links() -> typing.Sequence[typing.Tuple[int, int]]:
    """
    Get the list of linked instrument and object ID pairs.

    :return: a list of tuples containing the instrument ID and object ID of
        each linked instrument and object pair
    """
    instruments = models.Instrument.query.filter(models.Instrument.object_id != db.null()).all()
    return [
        (instrument.id, typing.cast(int, instrument.object_id))
        for instrument in instruments
    ]


def get_instruments_for_topic(
        topic_id: int
) -> typing.List[Instrument]:
    """
    Get the list of instruments assigned to a given topic.

    :param topic_id: the ID of an existing topic
    :return: the list of instruments
    :raise errors.TopicDoesNotExistError: if the topic does not exist
    """
    instruments = models.instruments.Instrument.query.filter(models.Instrument.topics.any(models.topics.Topic.id == topic_id)).all()
    if not instruments:
        topics.check_topic_exists(topic_id)
    return [
        Instrument.from_database(instrument)
        for instrument in instruments
    ]
