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
from . import errors, instruments, users, user_log, objects
from .notifications import create_notification_for_a_new_instrument_log_entry, create_notification_for_an_edited_instrument_log_entry
from ..models import instrument_log_entries
from ..models.instrument_log_entries import InstrumentLogCategoryTheme


class InstrumentLogEntry(
    collections.namedtuple(
        'InstrumentLogEntry',
        ['id', 'instrument_id', 'user_id', 'versions']
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
            versions: typing.Tuple['InstrumentLogEntryVersion'] = ()
    ):
        self = super(InstrumentLogEntry, cls).__new__(
            cls, id, instrument_id, user_id, versions
        )
        return self

    @classmethod
    def from_database(cls, instrument_log_entry: instrument_log_entries.InstrumentLogEntry) -> 'InstrumentLogEntry':
        return InstrumentLogEntry(
            id=instrument_log_entry.id,
            instrument_id=instrument_log_entry.instrument_id,
            user_id=instrument_log_entry.user_id,
            versions=tuple(sorted([
                InstrumentLogEntryVersion.from_database(version)
                for version in instrument_log_entry.versions
            ], key=lambda v: (v.utc_datetime, v.version_id)))
        )

    @property
    def author(self):
        return users.get_user(self.user_id)

    @property
    def file_attachments(self) -> typing.List['InstrumentLogFileAttachment']:
        return get_instrument_log_file_attachments(self.id)

    @property
    def object_attachments(self) -> typing.List['InstrumentLogObjectAttachment']:
        return get_instrument_log_object_attachments(self.id)


class InstrumentLogEntryVersion(
    collections.namedtuple(
        'InstrumentLogEntryVersion',
        ['log_entry_id', 'version_id', 'content', 'utc_datetime', 'categories', 'content_is_markdown', 'event_utc_datetime']
    )
):
    """
    This class provides an immutable wrapper around models.instrument_log_entries.InstrumentLogEntryVersion.
    """

    def __new__(
            cls,
            log_entry_id: int,
            version_id: int,
            content: str,
            utc_datetime: datetime.datetime,
            categories: typing.List['InstrumentLogCategory'],
            content_is_markdown: bool = False,
            event_utc_datetime: typing.Optional[datetime.datetime] = None
    ):
        self = super(InstrumentLogEntryVersion, cls).__new__(
            cls, log_entry_id, version_id, content, utc_datetime, categories, content_is_markdown, event_utc_datetime
        )
        return self

    @classmethod
    def from_database(cls, instrument_log_entry_version: instrument_log_entries.InstrumentLogEntryVersion) -> 'InstrumentLogEntryVersion':
        return InstrumentLogEntryVersion(
            log_entry_id=instrument_log_entry_version.log_entry_id,
            version_id=instrument_log_entry_version.version_id,
            content=instrument_log_entry_version.content,
            utc_datetime=instrument_log_entry_version.utc_datetime,
            categories=[
                InstrumentLogCategory.from_database(category)
                for category in sorted(instrument_log_entry_version.categories, key=lambda category: category.theme.value)
            ],
            content_is_markdown=instrument_log_entry_version.content_is_markdown,
            event_utc_datetime=instrument_log_entry_version.event_utc_datetime
        )


class InstrumentLogFileAttachment(
    collections.namedtuple(
        'InstrumentLogFileAttachment',
        ['id', 'log_entry_id', 'file_name', 'content', 'is_hidden']
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
            content: bytes,
            is_hidden: bool = False
    ):
        self = super(InstrumentLogFileAttachment, cls).__new__(
            cls, id, log_entry_id, file_name, content, is_hidden
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
            content=instrument_log_file_attachment.content,
            is_hidden=instrument_log_file_attachment.is_hidden
        )


class InstrumentLogObjectAttachment(
    collections.namedtuple(
        'InstrumentLogObjectAttachment',
        ['id', 'log_entry_id', 'object_id', 'is_hidden']
    )
):
    """
    This class provides an immutable wrapper around models.instrument_log_entries.InstrumentLogObjectAttachment.
    """

    def __new__(
            cls,
            id: int,
            log_entry_id: int,
            object_id: int,
            is_hidden: bool = False
    ):
        self = super(InstrumentLogObjectAttachment, cls).__new__(
            cls, id, log_entry_id, object_id, is_hidden
        )
        return self

    @classmethod
    def from_database(
            cls,
            instrument_log_object_attachment: instrument_log_entries.InstrumentLogObjectAttachment
    ) -> 'InstrumentLogObjectAttachment':
        return InstrumentLogObjectAttachment(
            id=instrument_log_object_attachment.id,
            log_entry_id=instrument_log_object_attachment.log_entry_id,
            object_id=instrument_log_object_attachment.object_id,
            is_hidden=instrument_log_object_attachment.is_hidden
        )


class InstrumentLogCategory(
    collections.namedtuple(
        'InstrumentLogCategory',
        ['id', 'instrument_id', 'title', 'theme']
    )
):
    """
    This class provides an immutable wrapper around models.instrument_log_entries.InstrumentLogCategory.
    """

    def __new__(
            cls,
            id: int,
            instrument_id: int,
            title: str,
            theme: instrument_log_entries.InstrumentLogCategoryTheme
    ):
        self = super(InstrumentLogCategory, cls).__new__(
            cls, id, instrument_id, title, theme
        )
        return self

    @classmethod
    def from_database(
            cls,
            category: instrument_log_entries.InstrumentLogCategory
    ) -> 'InstrumentLogCategory':
        return InstrumentLogCategory(
            id=category.id,
            instrument_id=category.instrument_id,
            title=category.title,
            theme=category.theme
        )


def get_instrument_log_categories(instrument_id: int) -> typing.List[InstrumentLogCategory]:
    """
    Return the instrument log categories for an object.

    :param instrument_id: the ID of an existing instrument
    :return: the instrument log categories
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    categories = instrument_log_entries.InstrumentLogCategory.query.filter_by(instrument_id=instrument_id).all()
    if not categories:
        # ensure that the instrument exists
        instruments.get_instrument(instrument_id=instrument_id)
        return []
    return [
        InstrumentLogCategory.from_database(category)
        for category in categories
    ]


def create_instrument_log_category(
    instrument_id: int,
    title: str,
    theme: instrument_log_entries.InstrumentLogCategoryTheme
) -> InstrumentLogCategory:
    """
    Create a new instrument log category for an instrument.

    :param instrument_id: the ID of an existing instrument
    :param title: the category title
    :param theme: the category theme
    :return: the newly created category
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    """
    category = instrument_log_entries.InstrumentLogCategory(
        instrument_id=instrument_id,
        title=title,
        theme=theme
    )
    db.session.add(category)
    db.session.commit()
    return InstrumentLogCategory.from_database(category)


def update_instrument_log_category(
    category_id: int,
    title: str,
    theme: InstrumentLogCategoryTheme
) -> InstrumentLogCategory:
    """

    :param category_id:
    :param title:
    :param theme:
    :return: the updated log category
    :raise errors.InstrumentLogCategoryDoesNotExistError: when no log category
        with the given ID exists
    """
    category = instrument_log_entries.InstrumentLogCategory.query.filter_by(id=category_id).first()
    if category is None:
        raise errors.InstrumentLogCategoryDoesNotExistError()
    category.title = title
    category.theme = theme
    db.session.add(category)
    db.session.commit()
    return InstrumentLogCategory.from_database(category)


def delete_instrument_log_category(category_id: int) -> None:
    category = instrument_log_entries.InstrumentLogCategory.query.filter_by(id=category_id).first()
    if category is None:
        raise errors.InstrumentLogCategoryDoesNotExistError()
    db.session.delete(category)
    db.session.commit()


def create_instrument_log_entry(
        instrument_id: int,
        user_id: int,
        content: str,
        category_ids: typing.Sequence[int] = (),
        content_is_markdown: bool = False,
        event_utc_datetime: typing.Optional[datetime.datetime] = None
) -> InstrumentLogEntry:
    """
    Create a new instrument log entry and adds it to the user log.

    :param instrument_id: the ID of an existing instrument
    :param user_id: the ID of an existing user
    :param content: the text content for the new log entry
    :param category_ids: the instrument-specific log category IDs
    :param content_is_markdown: whether or not the content is Markdown
    :param event_utc_datetime: the datetime when the logged event occurred
    :raise errors.InstrumentDoesNotExistError: when no instrument with the
        given instrument ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.InstrumentLogCategoryDoesNotExistError: when no log category
        with the given ID exists for this instrument
    """
    # ensure that the instrument exists
    instrument = instruments.get_instrument(instrument_id=instrument_id)
    # ensure that the user exists
    users.get_user(user_id)
    categories = []
    for category_id in set(category_ids):
        category = instrument_log_entries.InstrumentLogCategory.query.filter_by(
            id=category_id,
            instrument_id=instrument_id
        ).first()
        if category:
            categories.append(category)
        else:
            raise errors.InstrumentLogCategoryDoesNotExistError()
    instrument_log_entry = instrument_log_entries.InstrumentLogEntry(
        instrument_id=instrument_id,
        user_id=user_id
    )
    db.session.add(instrument_log_entry)
    db.session.commit()
    instrument_log_entry_version = instrument_log_entries.InstrumentLogEntryVersion(
        log_entry_id=instrument_log_entry.id,
        version_id=1,
        content=content,
        content_is_markdown=content_is_markdown,
        event_utc_datetime=event_utc_datetime
    )
    instrument_log_entry_version.categories = list(categories)
    db.session.add(instrument_log_entry_version)
    db.session.commit()
    user_log.create_instrument_log_entry(
        user_id=user_id,
        instrument_id=instrument_id,
        instrument_log_entry_id=instrument_log_entry.id
    )
    for responsible_user in instrument.responsible_users:
        if responsible_user.id != user_id:
            create_notification_for_a_new_instrument_log_entry(
                user_id=responsible_user.id,
                instrument_log_entry_id=instrument_log_entry.id
            )
    return InstrumentLogEntry.from_database(instrument_log_entry)


def update_instrument_log_entry(
        log_entry_id: int,
        content: str,
        category_ids: typing.Sequence[int] = (),
        content_is_markdown: bool = False,
        event_utc_datetime: typing.Optional[datetime.datetime] = None
) -> InstrumentLogEntry:
    """
    Update an existing instrument log entry.

    :param log_entry_id: the ID of an existing instrument log entry
    :param content: the text content for the new log entry
    :param category_ids: the instrument-specific log category IDs
    :param content_is_markdown: whether or not the content is Markdown
    :param event_utc_datetime: the datetime when the logged event occurred
    :raise errors.InstrumentLogEntryDoesNotExistError: when no instrument log
        entry with the given ID exists
    :raise errors.InstrumentLogCategoryDoesNotExistError: when no log category
        with the given ID exists for this instrument
    """
    # ensure that the instrument exists
    instrument_log_entry = instrument_log_entries.InstrumentLogEntry.query.filter_by(id=log_entry_id).first()
    if instrument_log_entry is None:
        raise errors.InstrumentLogEntryDoesNotExistError()
    instrument_id = instrument_log_entry.instrument_id
    categories = []
    for category_id in set(category_ids):
        category = instrument_log_entries.InstrumentLogCategory.query.filter_by(
            id=category_id,
            instrument_id=instrument_id
        ).first()
        if category:
            categories.append(category)
        else:
            raise errors.InstrumentLogCategoryDoesNotExistError()

    next_version_id = max(
        v.version_id
        for v in instrument_log_entry.versions
    ) + 1

    instrument_log_entry_version = instrument_log_entries.InstrumentLogEntryVersion(
        log_entry_id=instrument_log_entry.id,
        version_id=next_version_id,
        content=content,
        content_is_markdown=content_is_markdown,
        event_utc_datetime=event_utc_datetime
    )
    db.session.add(instrument_log_entry_version)
    instrument_log_entry_version.categories = list(categories)
    db.session.commit()

    instrument = instruments.get_instrument(instrument_log_entry.instrument_id)

    for responsible_user in instrument.responsible_users:
        if responsible_user.id != instrument_log_entry.user_id:
            create_notification_for_an_edited_instrument_log_entry(
                user_id=responsible_user.id,
                instrument_log_entry_id=instrument_log_entry.id,
                version_id=next_version_id
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
    ).all()
    log_entries.sort(key=lambda e: e.versions[0].utc_datetime)
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
    Return an instrument log entry file attachment.

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


def create_instrument_log_object_attachment(
        instrument_log_entry_id: int,
        object_id: int
) -> None:
    """
    Create an object attachment to a instrument log entry.

    :param instrument_log_entry_id: the ID of an existing instrument log entry
    :param object_id: the ID of an existing object
    :raise errors.InstrumentLogEntryDoesNotExistError: when no instrument log
        entry with the given ID exists
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    # ensure that the instrument log entry exists
    log_entry = get_instrument_log_entry(instrument_log_entry_id)
    # ensure the object exists
    objects.get_object(object_id)
    attachment = instrument_log_entries.InstrumentLogObjectAttachment(
        log_entry_id=log_entry.id,
        object_id=object_id
    )
    db.session.add(attachment)
    db.session.commit()


def get_instrument_log_object_attachments(
        instrument_log_entry_id: int
) -> typing.List[InstrumentLogObjectAttachment]:
    """
    Return a list of all object attachments for an instrument log entry.

    :param instrument_log_entry_id: the ID of an existing instrument log entry
    :return: the list of object attachments
    :raise errors.InstrumentLogEntryDoesNotExistError: when no instrument log
        entry with the given ID exists
    """
    # ensure that the instrument log entry exists
    log_entry = get_instrument_log_entry(instrument_log_entry_id)
    attachments = instrument_log_entries.InstrumentLogObjectAttachment.query.filter_by(
        log_entry_id=log_entry.id
    ).order_by(instrument_log_entries.InstrumentLogObjectAttachment.id).all()
    return [
        InstrumentLogObjectAttachment.from_database(attachment)
        for attachment in attachments
    ]


def get_instrument_log_object_attachment(
        instrument_log_object_attachment_id: int
) -> InstrumentLogObjectAttachment:
    """
    Return an instrument log entry object attachment.

    :param instrument_log_object_attachment_id: the ID of an existing
        instrument log object attachment
    :return: the object attachment with the given ID
    :raise errors.InstrumentLogObjectAttachmentDoesNotExistError: when no
        instrument log entry object attachment with the given ID exists
    """
    attachment = instrument_log_entries.InstrumentLogObjectAttachment.query.filter_by(
        id=instrument_log_object_attachment_id
    ).first()
    if attachment is None:
        raise errors.InstrumentLogObjectAttachmentDoesNotExistError()
    return InstrumentLogObjectAttachment.from_database(attachment)


def hide_instrument_log_object_attachment(
        instrument_log_object_attachment_id: int,
        set_hidden: bool = True
) -> None:
    """
    Hide an instrument log entry object attachment.

    :param instrument_log_object_attachment_id: the ID of an existing
        instrument log object attachment
    :param set_hidden: whether or not the attachment should be hidden
    :raise errors.InstrumentLogObjectAttachmentDoesNotExistError: when no
        instrument log entry object attachment with the given ID exists
    """
    attachment = instrument_log_entries.InstrumentLogObjectAttachment.query.filter_by(
        id=instrument_log_object_attachment_id
    ).first()
    if attachment is None:
        raise errors.InstrumentLogObjectAttachmentDoesNotExistError()
    attachment.is_hidden = set_hidden
    db.session.add(attachment)
    db.session.commit()


def hide_instrument_log_file_attachment(
        instrument_log_file_attachment_id: int
) -> None:
    """
    Hide an instrument log entry file attachment.

    :param instrument_log_file_attachment_id: the ID of an existing
        instrument log file attachment
    :raise errors.InstrumentLogFileAttachmentDoesNotExistError: when no
        instrument log entry file attachment with the given ID exists
    """
    attachment = instrument_log_entries.InstrumentLogFileAttachment.query.filter_by(
        id=instrument_log_file_attachment_id
    ).first()
    if attachment is None:
        raise errors.InstrumentLogFileAttachmentDoesNotExistError()
    attachment.is_hidden = True
    db.session.add(attachment)
    db.session.commit()
