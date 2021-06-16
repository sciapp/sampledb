# coding: utf-8
"""
Logic module for files

Users with WRITE permissions can upload files for samples or measurements. These
files are read only, so to edit an already uploaded file the user will have to
re-upload it. Accordingly, this module only allows creating new files and reading
existing ones.

As multiple files with the same name may exist, a per-object file id is used as
prefix for the actual file names on disk. For each sample or measurement, at
most 10000 files may be uploaded. This limit is arbitrary, but it should be big
enough so that it will not be encountered in practice. As a result, the prefix
will always be 5 characters in length (0000_ to 9999_). The actual file name
may be up to 150 bytes in length (bytes, not characters, encoded as UTF-8).

The files are stored in a directory named after the object's ID, which in turn
will be inside folders named after the action's ID.
"""

import collections
import datetime
import io
import os
import typing

from .. import db
from . import user_log, object_log, objects, users
from ..models import files
from ..models.file_log import FileLogEntry, FileLogEntryType
from .errors import FileNameTooLongError, TooManyFilesForObjectError, FileDoesNotExistError, InvalidFileStorageError

FILE_STORAGE_PATH: str = None
MAX_NUM_FILES: int = 10000


class File(collections.namedtuple('File', ['id', 'object_id', 'user_id', 'utc_datetime', 'data', 'binary_data'])):
    """
    This class provides an immutable wrapper around models.files.File.
    """

    def __new__(
            cls,
            id: int,
            object_id: int,
            user_id: int,
            utc_datetime: typing.Optional[datetime.datetime] = None,
            data: typing.Optional[typing.Dict[str, typing.Any]] = None,
            binary_data: typing.Optional[bytes] = None
    ):
        self = super(File, cls).__new__(cls, id, object_id, user_id, utc_datetime, data, binary_data)
        self._is_hidden = None
        self._hide_reason = None
        self._title = None
        self._description = None
        return self

    @classmethod
    def from_database(cls, file: files.File) -> 'File':
        if file.data is not None:
            data = file.data
        else:
            data = {
                'storage': 'local',
                'original_file_name': file.original_file_name
            }
        return File(
            id=file.id,
            object_id=file.object_id,
            user_id=file.user_id,
            utc_datetime=file.utc_datetime,
            data=data,
            binary_data=file.binary_data
        )

    @property
    def storage(self) -> str:
        return self.data.get('storage', 'local')

    @property
    def original_file_name(self):
        if self.storage in {'local', 'database'}:
            return self.data['original_file_name']
        else:
            raise InvalidFileStorageError()

    @property
    def real_file_name(self) -> str:
        if self.storage == 'local':
            # ensure that 4 digits are enough for every valid file ID
            assert MAX_NUM_FILES <= 10000
            # TODO: make the base path configurable
            object = objects.get_object(self.object_id)
            action_id = object.action_id
            prefixed_file_name = '{file_id:04d}_{file_name}'.format(file_id=self.id, file_name=self.original_file_name)
            return os.path.join(FILE_STORAGE_PATH, str(action_id), str(self.object_id), prefixed_file_name)
        else:
            raise InvalidFileStorageError()

    @property
    def url(self) -> str:
        if self.storage == 'url':
            return self.data['url']
        else:
            raise InvalidFileStorageError()

    @property
    def uploader(self) -> users.User:
        return users.get_user(self.user_id)

    @property
    def title(self) -> typing.Union[str, None]:
        if self._title is None:
            log_entry = FileLogEntry.query.filter_by(
                object_id=self.object_id,
                file_id=self.id,
                type=FileLogEntryType.EDIT_TITLE
            ).order_by(FileLogEntry.utc_datetime.desc()).first()
            if log_entry is None:
                if self.storage in {'local', 'database'}:
                    return self.original_file_name
                elif self.storage == 'url':
                    return self.data['url']
                else:
                    raise InvalidFileStorageError()
            self._title = log_entry.data['title']
        return self._title

    @property
    def description(self) -> typing.Union[str, None]:
        if self._description is None:
            log_entry = FileLogEntry.query.filter_by(
                object_id=self.object_id,
                file_id=self.id,
                type=FileLogEntryType.EDIT_DESCRIPTION
            ).order_by(FileLogEntry.utc_datetime.desc()).first()
            if log_entry is None:
                return None
            self._description = log_entry.data['description']
        return self._description

    @property
    def log_entries(self):
        return FileLogEntry.query.filter_by(
            object_id=self.object_id,
            file_id=self.id
        ).order_by(FileLogEntry.utc_datetime.asc()).all()

    @property
    def is_hidden(self):
        if self._is_hidden is None:
            log_entry = FileLogEntry.query.filter_by(
                object_id=self.object_id,
                file_id=self.id,
                type=FileLogEntryType.HIDE_FILE
            ).order_by(FileLogEntry.utc_datetime.desc()).first()
            if log_entry is None:
                self._is_hidden = False
                return False
            hide_time = log_entry.utc_datetime
            self._hide_reason = log_entry.data['reason']
            log_entry = FileLogEntry.query.filter_by(
                object_id=self.object_id,
                file_id=self.id,
                type=FileLogEntryType.UNHIDE_FILE
            ).order_by(FileLogEntry.utc_datetime.desc()).first()
            if log_entry is None:
                self._is_hidden = True
                return True
            unhide_time = log_entry.utc_datetime
            self._is_hidden = hide_time > unhide_time
        return self._is_hidden

    @property
    def hide_reason(self):
        if self.is_hidden:
            return self._hide_reason
        return None

    def open(self, read_only: bool = True) -> typing.BinaryIO:
        if self.storage == 'local':
            file_name = self.real_file_name
            if read_only:
                mode = 'rb'
            else:
                # before creating the file, the parent directories need exist
                os.makedirs(os.path.dirname(file_name), exist_ok=True)
                mode = 'xb'
            return open(file_name, mode)
        elif self.storage == 'database':
            if self.binary_data is not None:
                return io.BytesIO(self.binary_data)
            else:
                return io.BytesIO(b'')
        else:
            raise InvalidFileStorageError()


def create_local_file(object_id: int, user_id: int, file_name: str, save_content: typing.Callable[[typing.BinaryIO], None]) -> File:
    """
    Create a new local file and add it to the object and user logs.

    The function will call save_content with the opened file (in binary mode).

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param file_name: the original file name
    :param save_content: a function which will save the file's content to the
        given stream. The function will be called at most once.
    :return: the newly created file
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.FileNameTooLongError: when the file name is longer than 150
        bytes when encoded as UTF-8
    :raise errors.TooManyFilesForObjectError: when there are already 10000
        files for the object with the given id
    """
    # ensure that the file name is valid
    if len(file_name.encode('utf8')) > 150:
        raise FileNameTooLongError()

    db_file = _create_db_file(
        object_id=object_id,
        user_id=user_id,
        data={
            'storage': 'local',
            'original_file_name': file_name
        }
    )
    file = File.from_database(db_file)
    try:
        with file.open(read_only=False) as storage_file:
            save_content(storage_file)
    except Exception:
        db.session.delete(db_file)
        db.session.commit()
        raise
    _create_file_logs(file)
    return file


def create_url_file(object_id: int, user_id: int, url: str) -> File:
    """
    Create a file as a link to a URL and add it to the object and user logs.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param url: the file URL
    :return: the newly created file
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.TooManyFilesForObjectError: when there are already 10000
        files for the object with the given id
    """
    db_file = _create_db_file(
        object_id=object_id,
        user_id=user_id,
        data={
            'storage': 'url',
            'url': url
        }
    )
    file = File.from_database(db_file)
    _create_file_logs(file)
    return file


def create_database_file(object_id: int, user_id: int, file_name: str, save_content: typing.Callable[[typing.BinaryIO], None]) -> File:
    """
    Create a new database file and add it to the object and user logs.

    The function will call save_content with an opened file (in binary mode).

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param file_name: the original file name
    :param save_content: a function which will save the file's content to the
        given stream. The function will be called at most once.
    :return: the newly created file
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.FileNameTooLongError: when the file name is longer than 150
        bytes when encoded as UTF-8
    """
    # ensure that the file name is valid
    if len(file_name.encode('utf8')) > 150:
        raise FileNameTooLongError()

    binary_data_file = io.BytesIO()
    save_content(binary_data_file)
    binary_data = binary_data_file.getvalue()

    db_file = _create_db_file(
        object_id=object_id,
        user_id=user_id,
        data={
            'storage': 'database',
            'original_file_name': file_name
        }
    )
    db_file.binary_data = binary_data
    db.session.commit()
    file = File.from_database(db_file)
    _create_file_logs(file)
    return file


def _create_file_logs(file: File) -> None:
    """
    Create object and user logs for a new file.

    :param file: the file to create log entries for
    """
    file_id = file.id
    object_id = file.object_id
    user_id = file.user_id
    object_log.upload_file(user_id=user_id, object_id=object_id, file_id=file_id)
    user_log.upload_file(user_id=user_id, object_id=object_id, file_id=file_id)


def _create_db_file(
        object_id: int,
        user_id: int,
        data: typing.Dict[str, typing.Any]
) -> files.File:
    """
    Creates a new file in the database.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param data: the file storage data
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.TooManyFilesForObjectError: when there are already 10000
        files for the object with the given id
    """
    # ensure that the object exists
    object = objects.get_object(object_id)
    # ensure that the user exists
    users.get_user(user_id)
    # calculate the next file id
    previous_file_id = db.session.query(db.func.max(files.File.id)).filter(files.File.object_id == object.id).scalar()
    if previous_file_id is None:
        file_id = 0
    else:
        file_id = previous_file_id + 1
    if file_id >= MAX_NUM_FILES:
        raise TooManyFilesForObjectError()
    db_file = files.File(
        file_id=file_id,
        object_id=object_id,
        user_id=user_id,
        data=data
    )
    db.session.add(db_file)
    db.session.commit()
    return db_file


def update_file_information(object_id: int, file_id: int, user_id: int, title: str, description: str) -> None:
    """
    Creates new file log entries for updating a file's information.

    :param object_id: the ID of an existing object
    :param file_id: the ID of a file for the object
    :param user_id: the ID of an existing user
    :param title: the new title
    :param description: the new description
    :raise errors.FileDoesNotExistError: when no file with the given object ID
        and file ID exists
    """
    file = get_file_for_object(object_id=object_id, file_id=file_id)
    if file is None:
        raise FileDoesNotExistError()
    if not title:
        title = file.original_file_name
    if title != file.title:
        log_entry = FileLogEntry(type=FileLogEntryType.EDIT_TITLE, object_id=object_id, file_id=file_id, user_id=user_id, data={
            'title': title
        })
        db.session.add(log_entry)
        db.session.commit()
    if description != file.description and not (description == "" and file.description is None):
        log_entry = FileLogEntry(type=FileLogEntryType.EDIT_DESCRIPTION, object_id=object_id, file_id=file_id, user_id=user_id, data={
            'description': description
        })
        db.session.add(log_entry)
        db.session.commit()


def hide_file(object_id: int, file_id: int, user_id: int, reason: str) -> None:
    """
    Hides a file.

    :param object_id: the ID of an existing object
    :param file_id: the ID of a file for the object
    :param user_id: the ID of an existing user
    :param reason: the reason for hiding the file
    :raise errors.FileDoesNotExistError: when no file with the given object ID
        and file ID exists
    """
    file = get_file_for_object(object_id=object_id, file_id=file_id)
    if file is None:
        raise FileDoesNotExistError()
    if not reason:
        reason = ''
    log_entry = FileLogEntry(type=FileLogEntryType.HIDE_FILE, object_id=object_id, file_id=file_id, user_id=user_id, data={
        'reason': reason
    })
    db.session.add(log_entry)
    db.session.commit()


def get_file_for_object(object_id: int, file_id: int) -> typing.Optional[File]:
    """
    Returns the file with the given file ID for the object with the given object ID.

    :param object_id: the ID of an existing object
    :param file_id: the ID of an existing file for the object
    :return: the file or None
    """
    db_file = files.File.query.filter_by(object_id=object_id, id=file_id).first()
    if db_file is None:
        return None
    return File.from_database(db_file)


def get_files_for_object(object_id: int) -> typing.List[File]:
    """
    Returns a list of files for an object.

    :param object_id: the ID of an existing object
    :return: the list of files, sorted by upload time from first to last
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    db_files = files.File.query.filter_by(object_id=object_id).order_by(db.asc(files.File.utc_datetime)).all()
    if not db_files:
        # ensure that the object exists
        objects.get_object(object_id)
    return [File.from_database(db_file) for db_file in db_files]
