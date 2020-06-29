# coding: utf-8
"""
Logic module for instrument log entries

Instrument scientists can add messages to a log for their instruments. They
can also allow users to provide log entries, e.g. to report issues. These log
entries are immutable and therefore this module only allows the creation and
querying of comments.

Files can be attached to these log entries, e.g. to supply the instrument scientists
with control files or photographs of an experiment setup.
"""

import collections
import datetime
import typing

from .. import db
from . import errors, instruments, users, user_log, notifications
from ..models import instrument_log_entries


class InstrumentLogEntry(
    collections.namedtuple(
        'InstrumentLogEntry',
        ['id', 'instrument_id', 'user_id', 'content', 'utc_datetime']
    )
):
    """
    This class provides an immutable wrapper around models.instrument_log_entries.InstrumentLogEntry.
    """

    def __new__(
            cls,
            id: int,
            instrument_id: int,
            user_id: int,
            content: str,
            utc_datetime: datetime.datetime
    ):
        self = super(InstrumentLogEntry, cls).__new__(
            cls, id, instrument_id, user_id, content, utc_datetime
        )
        return self

    @classmethod
    def from_database(cls, instrument_log_entry: instrument_log_entries.InstrumentLogEntry) -> 'InstrumentLogEntry':
        return InstrumentLogEntry(
            id=instrument_log_entry.id,
            instrument_id=instrument_log_entry.instrument_id,
            user_id=instrument_log_entry.user_id,
            content=instrument_log_entry.content,
            utc_datetime=instrument_log_entry.utc_datetime
        )

    @property
    def author(self):
        return users.get_user(self.user_id)

    @property
    def file_attachments(self) -> typing.List['InstrumentLogFileAttachment']:
        return get_instrument_log_file_attachments(self.id)


class InstrumentLogFileAttachment(
    collections.namedtuple(
        'InstrumentLogFileAttachment',
        ['id', 'log_entry_id', 'file_name', 'content']
    )
):
    """
    This class provides an immutable wrapper around models.instrument_log_entries.InstrumentLogFileAttachment.
    """

    def __new__(
            cls,
            id: int,
            log_entry_id: int,
            file_name: str,
            content: bytes
    ):
        self = super(InstrumentLogFileAttachment, cls).__new__(
            cls, id, log_entry_id, file_name, content
        )
        return self

    @classmethod
    def from_database(
            cls,
            instrument_log_file_attachment: instrument_log_entries.InstrumentLogFileAttachment
    ) -> 'InstrumentLogFileAttachment':
        return InstrumentLogFileAttachment(
            id=instrument_log_file_attachment.id,
            log_entry_id=instrument_log_file_attachment.log_entry_id,
            file_name=instrument_log_file_attachment.file_name,
            content=instrument_log_file_attachment.content
        )


def create_instrument_log_entry(
        instrument_id: int,
        user_id: int,
        content: str
) -> InstrumentLogEntry:
    """
    Creates a new instrument log entry and adds it to the user log.

    :param instrument_id: the ID of an existing instrument
    :param user_id: the ID of an existing user
    :param content: the text content for the new comment
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure that the object exists
    instrument = instruments.get_instrument(instrument_id=instrument_id)
    # ensure that the user exists
    users.get_user(user_id)
    instrument_log_entry = instrument_log_entries.InstrumentLogEntry(
        instrument_id=instrument_id,
        user_id=user_id,
        content=content
    )
    db.session.add(instrument_log_entry)
    db.session.commit()
    user_log.create_instrument_log_entry(
        user_id=user_id,
        instrument_id=instrument_id,
        instrument_log_entry_id=instrument_log_entry.id
    )
    for responsible_user in instrument.responsible_users:
        if responsible_user.id != user_id:
            notifications.create_notification_for_a_new_instrument_log_entry(
                user_id=responsible_user.id,
                instrument_log_entry_id=instrument_log_entry.id
            )
    return InstrumentLogEntry.from_database(instrument_log_entry)


def get_instrument_log_entry(instrument_log_entry_id: int) -> InstrumentLogEntry:
    """
    Return an individual instrument log entry.

    :param instrument_log_entry_id: the ID of an existing instrument log entry
    :raise errors.InstrumentLogEntryDoesNotExistError: when no instrument log
        entry with the given ID exists
    """
    log_entry = instrument_log_entries.InstrumentLogEntry.query.filter_by(
        id=instrument_log_entry_id
    ).first()
    if log_entry is None:
        raise errors.InstrumentLogEntryDoesNotExistError()
    return InstrumentLogEntry.from_database(log_entry)


def get_instrument_log_entries(instrument_id: int) -> typing.List[InstrumentLogEntry]:
    """
    Returns a list of log entries for an instrument.

    :param instrument_id: the ID of an existing instrument
    :return: the list of log entries, sorted from oldest to newest
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    log_entries = instrument_log_entries.InstrumentLogEntry.query.filter_by(
        instrument_id=instrument_id
    ).order_by(
        db.asc(instrument_log_entries.InstrumentLogEntry.utc_datetime)
    ).all()
    if not log_entries:
        # ensure that the instrument exists
        instruments.get_instrument(instrument_id)
    return [
        InstrumentLogEntry.from_database(log_entry)
        for log_entry in log_entries
    ]


def create_instrument_log_file_attachment(
        instrument_log_entry_id: int,
        file_name: str,
        content: bytes
) -> None:
    """
    Create a file attachment to a instrument log entry.

    :param instrument_log_entry_id: the ID of an existing instrument log entry
    :param file_name: the original file name
    :param content: the file content
    :raise errors.InstrumentLogEntryDoesNotExistError: when no instrument log
        entry with the given ID exists
    """
    # ensure that the instrument log entry exists
    log_entry = get_instrument_log_entry(instrument_log_entry_id)
    attachment = instrument_log_entries.InstrumentLogFileAttachment(
        log_entry_id=log_entry.id,
        file_name=file_name,
        content=content
    )
    db.session.add(attachment)
    db.session.commit()


def get_instrument_log_file_attachments(
        instrument_log_entry_id: int
) -> typing.List[InstrumentLogFileAttachment]:
    """
    Return a list of all file attachments for an instrument log entry.

    :param instrument_log_entry_id: the ID of an existing instrument log entry
    :return: the list of file attachments
    :raise errors.InstrumentLogEntryDoesNotExistError: when no instrument log
        entry with the given ID exists
    """
    # ensure that the instrument log entry exists
    log_entry = get_instrument_log_entry(instrument_log_entry_id)
    attachments = instrument_log_entries.InstrumentLogFileAttachment.query.filter_by(
        log_entry_id=log_entry.id
    ).order_by(instrument_log_entries.InstrumentLogFileAttachment.id).all()
    return [
        InstrumentLogFileAttachment.from_database(attachment)
        for attachment in attachments
    ]


def get_instrument_log_file_attachment(
        instrument_log_file_attachment_id: int
) -> InstrumentLogFileAttachment:
    """
    Return an instrument log entry file attachments.

    :param instrument_log_file_attachment_id: the ID of an existing instrument
        log file attachment
    :return: the file attachment with the given ID
    :raise errors.InstrumentLogFileAttachmentDoesNotExistError: when no
        instrument log entry file attachment with the given ID exists
    """
    attachment = instrument_log_entries.InstrumentLogFileAttachment.query.filter_by(
        id=instrument_log_file_attachment_id
    ).first()
    if attachment is None:
        raise errors.InstrumentLogFileAttachmentDoesNotExistError()
    return InstrumentLogFileAttachment.from_database(attachment)
