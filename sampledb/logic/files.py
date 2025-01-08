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

import dataclasses
import datetime
import hashlib
import io
import os
import typing

import flask
import requests
from flask_babel import gettext

from . import components, errors, object_log, objects, user_log, users
from .components import get_component
from .errors import FileDoesNotExistError, FileNameTooLongError, \
    InvalidFileStorageError, TooManyFilesForObjectError, FederationFileNotAvailableError
from .objects import get_object
from .users import get_user
from .. import db
from ..models import files
from ..models.file_log import FileLogEntry, FileLogEntryType

MAX_NUM_FILES: int = 10000

SUPPORTED_HASH_ALGORITHMS = ['sha256', 'sha512']
DEFAULT_HASH_ALGORITHM = 'sha256'


@dataclasses.dataclass(frozen=True)
class File:
    """
    This class provides an immutable wrapper around models.files.File.
    """
    id: int
    object_id: int
    user_id: typing.Optional[int]
    data: typing.Dict[str, typing.Any]
    _mutable_file: files.File
    utc_datetime: typing.Optional[datetime.datetime] = None
    fed_id: typing.Optional[int] = None
    component_id: typing.Optional[int] = None
    preview_image_mime_type: typing.Optional[str] = None

    @dataclasses.dataclass(frozen=True)
    class HashInfo:
        algorithm: str
        hexdigest: str

        @classmethod
        def from_binary_data(
                cls,
                algorithm: str,
                binary_data: bytes
        ) -> typing.Optional['File.HashInfo']:
            if algorithm not in SUPPORTED_HASH_ALGORITHMS:
                return None
            return cls(
                algorithm=algorithm,
                hexdigest=getattr(hashlib, algorithm)(binary_data).hexdigest()
            )

    hash: typing.Optional[HashInfo] = None

    @dataclasses.dataclass
    class InfoCache:
        is_hidden: typing.Optional[bool] = None
        hide_reason: typing.Optional[str] = None
        title: typing.Optional[str] = None
        url: typing.Optional[str] = None
        description: typing.Optional[str] = None

    _info_cache: InfoCache = dataclasses.field(default_factory=InfoCache, kw_only=True, repr=False, compare=False)

    @dataclasses.dataclass
    class DataCache:
        binary_data: typing.Optional[bytes] = None
        preview_image_binary_data: typing.Optional[bytes] = None
    _data_cache: DataCache = dataclasses.field(default_factory=DataCache, kw_only=True, repr=False, compare=False)

    @classmethod
    def from_database(cls, file: files.File) -> 'File':
        if file.data is not None:
            data = file.data
        else:
            data = {
                'storage': 'none'
            }
        if isinstance(data.get('hash'), dict):
            hash = File.HashInfo(
                algorithm=data['hash'].get('algorithm'),
                hexdigest=data['hash'].get('hexdigest')
            )
        else:
            hash = None
        return File(
            id=file.id,
            object_id=file.object_id,
            user_id=file.user_id,
            utc_datetime=file.utc_datetime,
            data=data,
            fed_id=file.fed_id,
            component_id=file.component_id,
            hash=hash,
            preview_image_mime_type=file.preview_image_mime_type,
            _mutable_file=file
        )

    @property
    def binary_data(self) -> typing.Optional[bytes]:
        if self._data_cache.binary_data is None:
            self._data_cache.binary_data = self._mutable_file.binary_data
        return self._data_cache.binary_data

    @property
    def preview_image_binary_data(self) -> typing.Optional[bytes]:
        if self._data_cache.preview_image_binary_data is None:
            self._data_cache.preview_image_binary_data = self._mutable_file.preview_image_binary_data
        return self._data_cache.preview_image_binary_data

    @property
    def storage(self) -> str:
        if self.data is None:
            return 'none'
        return str(self.data.get('storage', 'none'))

    @property
    def original_file_name(self) -> str:
        if self.data is not None and self.storage in {'database', 'federation'}:
            return str(self.data.get('original_file_name', ''))
        else:
            raise InvalidFileStorageError()

    @property
    def filepath(self) -> str:
        if self.data is not None and self.storage in {'local_reference'}:
            return str(self.data.get('filepath', ''))
        else:
            raise InvalidFileStorageError()

    @property
    def url(self) -> str:
        if self.data is not None and self.storage == 'url':
            if self._info_cache.url is None:
                log_entry = FileLogEntry.query.filter_by(
                    object_id=self.object_id,
                    file_id=self.id,
                    type=FileLogEntryType.EDIT_URL
                ).order_by(FileLogEntry.utc_datetime.desc()).first()
                if log_entry is not None:
                    self._info_cache.url = log_entry.data['url']
                else:
                    self._info_cache.url = self.data['url']
            return self._info_cache.url
        else:
            raise InvalidFileStorageError()

    @property
    def uploader(self) -> typing.Optional[users.User]:
        if self.user_id is None:
            return None
        return users.get_user(self.user_id)

    @property
    def title(self) -> typing.Optional[str]:
        if self._info_cache.title is None:
            self._info_cache.title = self.real_title
            if self._info_cache.title is None:
                if self.storage in {'database', 'federation'}:
                    return self.original_file_name
                elif self.storage == 'local_reference':
                    return self.filepath
                elif self.storage == 'url':
                    return self.url
                else:
                    raise InvalidFileStorageError()
        return self._info_cache.title

    @property
    def real_title(self) -> typing.Optional[str]:
        log_entry = FileLogEntry.query.filter_by(
            object_id=self.object_id,
            file_id=self.id,
            type=FileLogEntryType.EDIT_TITLE
        ).order_by(FileLogEntry.utc_datetime.desc()).first()
        if log_entry is None:
            return None
        if 'title' not in log_entry.data:
            return None
        return str(log_entry.data['title'])

    @property
    def description(self) -> typing.Union[str, None]:
        if self._info_cache.description is None:
            log_entry = FileLogEntry.query.filter_by(
                object_id=self.object_id,
                file_id=self.id,
                type=FileLogEntryType.EDIT_DESCRIPTION
            ).order_by(FileLogEntry.utc_datetime.desc()).first()
            if log_entry is None:
                return None
            self._info_cache.description = log_entry.data['description']
        return self._info_cache.description

    @property
    def log_entries(self) -> typing.List[FileLogEntry]:
        users_by_id: typing.Dict[typing.Optional[int], typing.Optional[users.User]] = {None: None}
        log_entries = []
        for log_entry in FileLogEntry.query.filter_by(
            object_id=self.object_id,
            file_id=self.id
        ).order_by(FileLogEntry.utc_datetime.asc()).all():
            if log_entry.user_id not in users_by_id:
                users_by_id[log_entry.user_id] = users.get_user(log_entry.user_id)
            log_entry.user = users_by_id[log_entry.user_id]
            log_entries.append(log_entry)
        return log_entries

    @property
    def is_hidden(self) -> bool:
        if self._info_cache.is_hidden is None:
            log_entry = FileLogEntry.query.filter_by(
                object_id=self.object_id,
                file_id=self.id,
                type=FileLogEntryType.HIDE_FILE
            ).order_by(FileLogEntry.utc_datetime.desc()).first()
            if log_entry is None:
                self._info_cache.is_hidden = False
                return False
            hide_time = log_entry.utc_datetime
            self._info_cache.hide_reason = log_entry.data['reason']
            log_entry = FileLogEntry.query.filter_by(
                object_id=self.object_id,
                file_id=self.id,
                type=FileLogEntryType.UNHIDE_FILE
            ).order_by(FileLogEntry.utc_datetime.desc()).first()
            if log_entry is None:
                self._info_cache.is_hidden = True
                return True
            unhide_time = log_entry.utc_datetime
            self._info_cache.is_hidden = hide_time > unhide_time
        return bool(self._info_cache.is_hidden)

    @property
    def hide_reason(self) -> typing.Optional[str]:
        if self.is_hidden:
            return self._info_cache.hide_reason
        return None

    def open(self, read_only: bool = True) -> typing.BinaryIO:
        if self.storage == 'database':
            if self.binary_data is not None:
                return io.BytesIO(self.binary_data)
            else:
                return io.BytesIO(b'')
        elif self.storage == 'federation':
            object = get_object(self.object_id)
            if self.component_id:
                component = get_component(self.component_id)
            else:
                raise InvalidFileStorageError()
            from .federation.update import get_binary
            try:
                file_data = get_binary(f'/federation/v1/shares/objects/{object.fed_object_id}/files/{self.fed_id}', component)
            except errors.UnauthorizedRequestError:
                raise FederationFileNotAvailableError()
            except errors.MissingComponentAddressError:
                raise FederationFileNotAvailableError()
            except errors.RequestServerError:
                raise FederationFileNotAvailableError()
            except errors.RequestError:
                raise FederationFileNotAvailableError()
            except requests.exceptions.ConnectionError:
                raise FederationFileNotAvailableError()
            except errors.NoAuthenticationMethodError:
                raise FederationFileNotAvailableError()
            return file_data
        else:
            raise InvalidFileStorageError()


def create_local_file_reference(
        object_id: int,
        user_id: int,
        filepath: str,
        hash: typing.Optional[File.HashInfo] = None
) -> File:
    """
    Create a file as a link to a local file and add it to the object and user
    logs.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param filepath: the filepath relative to the mounting directory of the
        download service
    :param hash: the hash info for this file
    :return: the newly created file
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.TooManyFilesForObjectError: when there are already 10000
        files for the object with the given id
    :raise errors.UnauthorizedRequestError: when the current user is not allowed to
        add this certain filepath
    """
    path_permissions: typing.Dict[str, typing.List[int]] = flask.current_app.config['DOWNLOAD_SERVICE_WHITELIST']
    user = get_user(user_id)

    filepath = os.path.normpath(filepath)
    for path, user_ids in path_permissions.items():
        if not path.endswith(os.sep):
            path += os.sep
        if filepath.startswith(path):
            if user.is_admin or user_id in user_ids:
                break
    else:
        raise errors.UnauthorizedRequestError()

    db_file = _create_db_file(
        object_id=object_id,
        user_id=user_id,
        data={
            'storage': 'local_reference',
            'filepath': filepath,
            'valid': True,  # to distinguish from local file references created before the whitelist was checked properly
            'hash': {
                'algorithm': hash.algorithm,
                'hexdigest': hash.hexdigest
            } if hash is not None else None
        }
    )
    file = File.from_database(db_file)
    _create_file_logs(file)
    return file


def create_url_file(
        object_id: int,
        user_id: int,
        url: str,
        *,
        create_log_entry: bool = True,
        utc_datetime: typing.Optional[datetime.datetime] = None
) -> File:
    """
    Create a file as a link to a URL and add it to the object and user logs.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param url: the file URL
    :param create_log_entry: whether to create a log entry
    :param utc_datetime: the datetime for the file, or None
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
        },
        utc_datetime=utc_datetime
    )
    file = File.from_database(db_file)
    if create_log_entry:
        _create_file_logs(file)
    return file


@typing.overload
def create_database_file(
        object_id: int,
        user_id: int,
        file_name: str,
        save_content: typing.Callable[[typing.BinaryIO], None],
        hash: typing.Optional[File.HashInfo] = None,
        *,
        create_log_entry: bool = True,
        preview_image_binary_data: bytes,
        preview_image_mime_type: str,
        utc_datetime: typing.Optional[datetime.datetime] = None
) -> File:
    ...


@typing.overload
def create_database_file(
        object_id: int,
        user_id: int,
        file_name: str,
        save_content: typing.Callable[[typing.BinaryIO], None],
        hash: typing.Optional[File.HashInfo] = None,
        *,
        create_log_entry: bool = True,
        preview_image_binary_data: None = None,
        preview_image_mime_type: None = None,
        utc_datetime: typing.Optional[datetime.datetime] = None
) -> File:
    ...


def create_database_file(
        object_id: int,
        user_id: int,
        file_name: str,
        save_content: typing.Callable[[typing.BinaryIO], None],
        hash: typing.Optional[File.HashInfo] = None,
        *,
        create_log_entry: bool = True,
        preview_image_binary_data: typing.Optional[bytes] = None,
        preview_image_mime_type: typing.Optional[str] = None,
        utc_datetime: typing.Optional[datetime.datetime] = None
) -> File:
    """
    Create a new database file and add it to the object and user logs.

    The function will call save_content with an opened file (in binary mode).

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param file_name: the original file name
    :param save_content: a function which will save the file's content to the
        given stream. The function will be called at most once.
    :param hash: the hash info for this file
    :param create_log_entry: whether to create a log entry
    :param preview_image_binary_data: binary data for the preview image, or None
    :param preview_image_mime_type: mime type for the preview image, or None
    :param utc_datetime: the datetime for the file, or None
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
    if hash is None:
        hash = File.HashInfo.from_binary_data(
            algorithm=DEFAULT_HASH_ALGORITHM,
            binary_data=binary_data
        )

    db_file = _create_db_file(
        object_id=object_id,
        user_id=user_id,
        data={
            'storage': 'database',
            'original_file_name': file_name,
            'hash': {
                'algorithm': hash.algorithm,
                'hexdigest': hash.hexdigest
            } if hash is not None else None
        },
        utc_datetime=utc_datetime
    )
    db_file.binary_data = binary_data
    db_file.preview_image_binary_data = preview_image_binary_data
    db_file.preview_image_mime_type = preview_image_mime_type.lower() if preview_image_mime_type else ''
    db.session.commit()
    file = File.from_database(db_file)
    if create_log_entry:
        _create_file_logs(file)
    return file


def get_mutable_file(
        file_id: int,
        object_id: int,
        component_id: typing.Optional[int] = None
) -> files.File:
    """
    :param file_id: the federated ID of the file
    :param object_id: ID of the object the requested file is assigned to
    :param component_id: the components ID (source)
    :return: the file
    """
    db_file: typing.Optional[files.File]
    if component_id is None:
        db_file = files.File.query.filter_by(id=file_id, object_id=object_id).first()
    else:
        db_file = files.File.query.filter_by(fed_id=file_id, object_id=object_id, component_id=component_id).first()
    if db_file is None:
        objects.check_object_exists(object_id)
        if component_id is not None:
            components.check_component_exists(component_id)
        raise errors.FileDoesNotExistError
    return db_file


def get_file(
        file_id: int,
        object_id: int,
        component_id: typing.Optional[int] = None
) -> File:
    """
    :param file_id: the federated ID of the file
    :param object_id: ID of the object the requested file is assigned to
    :param component_id: the components ID (source)
    :return: the file
    """
    return File.from_database(get_mutable_file(file_id=file_id, object_id=object_id, component_id=component_id))


def create_fed_file(
        object_id: int,
        user_id: typing.Optional[int],
        data: typing.Optional[typing.Dict[str, typing.Any]],
        save_content: typing.Optional[typing.Callable[[typing.BinaryIO], None]],
        utc_datetime: datetime.datetime,
        fed_id: int,
        component_id: int
) -> files.File:
    """
    Creates a new file referencing a federated file.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param data: data describing the file or file reference
    :param save_content: a function which will save the file's content to the
        given stream. The function will be called at most once.
    :param utc_datetime: the time of file-creation
    :param fed_id: the federated ID of the file
    :param component_id: the components ID (source)
    :return: the created File object
    :raise errors.ComponentDoesNotExistError: when no component with the given
        component ID exists
    """
    file = _create_db_file(object_id, user_id, data, utc_datetime, fed_id, component_id)
    if save_content:
        binary_data_file = io.BytesIO()
        save_content(binary_data_file)
        binary_data = binary_data_file.getvalue()
        file.binary_data = binary_data
        db.session.commit()
    return file


def _create_file_logs(file: File) -> None:
    """
    Create object and user logs for a new file.

    :param file: the file to create log entries for
    """
    file_id = file.id
    object_id = file.object_id
    user_id = file.user_id
    if user_id is not None:
        object_log.upload_file(user_id=user_id, object_id=object_id, file_id=file_id)
        user_log.upload_file(user_id=user_id, object_id=object_id, file_id=file_id)


def _create_db_file(
        object_id: int,
        user_id: typing.Optional[int],
        data: typing.Optional[typing.Dict[str, typing.Any]],
        utc_datetime: typing.Optional[datetime.datetime] = None,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None
) -> files.File:
    """
    Creates a new file in the database.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param data: the file storage data
    :param utc_datetime: the time of file-creation, only if file
        has been imported
    :param fed_id: the federated ID of the file, only if file
        has been imported
    :param component_id: the components ID (source), only if file
        has been imported
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.TooManyFilesForObjectError: when there are already 10000
        files for the object with the given id
    :raise errors.ComponentDoesNotExistError: when there is no component with the
        given ID
    """
    if (component_id is not None and (fed_id is None or utc_datetime is None)) or (component_id is None and (user_id is None or data is None or fed_id is not None)):
        raise TypeError('Invalid parameter combination.')

    # ensure that the object exists
    object = objects.get_object(object_id)
    if user_id is not None:
        # ensure that the user exists
        users.check_user_exists(user_id)
    if component_id is not None:
        # ensure that the component exists
        components.check_component_exists(component_id)
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
        data=data,
        utc_datetime=utc_datetime,
        fed_id=fed_id,
        component_id=component_id
    )
    db.session.add(db_file)
    db.session.commit()
    return db_file


def update_file_information(object_id: int, file_id: int, user_id: int, title: str, description: str, url: typing.Optional[str] = None) -> None:
    """
    Creates new file log entries for updating a file's information.

    :param object_id: the ID of an existing object
    :param file_id: the ID of a file for the object
    :param user_id: the ID of an existing user
    :param title: the new title
    :param description: the new description
    :param url: the new url
    :raise errors.FileDoesNotExistError: when no file with the given object ID
        and file ID exists
    """
    file = get_file_for_object(object_id=object_id, file_id=file_id)
    if file is None:
        raise FileDoesNotExistError()
    if not title:
        if file.storage == 'url':
            title = file.url
        else:
            title = file.original_file_name
    if title != file.real_title:
        log_entry = FileLogEntry(type=FileLogEntryType.EDIT_TITLE, object_id=object_id, file_id=file_id, user_id=user_id, data={
            'title': title
        })
        db.session.add(log_entry)
        db.session.commit()
    if url and file.storage == 'url' and url != file.url:
        log_entry = FileLogEntry(type=FileLogEntryType.EDIT_URL, object_id=object_id, file_id=file_id, user_id=user_id, data={
            'url': url
        })
        db.session.add(log_entry)
        db.session.commit()
    if description != file.description and not (description == "" and file.description is None):
        log_entry = FileLogEntry(type=FileLogEntryType.EDIT_DESCRIPTION, object_id=object_id, file_id=file_id, user_id=user_id, data={
            'description': description
        })
        db.session.add(log_entry)
        db.session.commit()


def hide_file(
        object_id: int,
        file_id: int,
        user_id: int,
        reason: str,
        utc_datetime: typing.Optional[datetime.datetime] = None
) -> None:
    """
    Hides a file.

    :param object_id: the ID of an existing object
    :param file_id: the ID of a file for the object
    :param user_id: the ID of an existing user
    :param reason: the reason for hiding the file
    :param utc_datetime: the time when the file was hidden or None to select the current time
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
    }, utc_datetime=utc_datetime)
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
        objects.check_object_exists(object_id)
    return [File.from_database(db_file) for db_file in db_files]


def get_file_names_by_id_for_object(
        object_id: int
) -> typing.Dict[int, typing.Tuple[str, str]]:
    files = get_files_for_object(object_id)
    file_names_by_id = {}
    for file in files:
        if file.storage in {'database', 'federation'}:
            actual_name = file.original_file_name
            if file.is_hidden:
                display_name = gettext('Hidden File') + f' #{file.id}'
            else:
                display_name = actual_name
            file_names_by_id[file.id] = (actual_name, display_name)
    return file_names_by_id
