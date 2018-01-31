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

import base64
import collections
import datetime
import itertools
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import typing

from .. import db
from . import user_log, object_log, objects, users
from ..models import files
from ..models.file_log import FileLogEntry, FileLogEntryType
from .errors import FileNameTooLongError, TooManyFilesForObjectError, InvalidFileSourceError, FileDoesNotExistError
from .ldap import get_posix_info, search_user
from .authentication import get_user_ldap_uid

FILE_STORAGE_PATH: str = None
MAX_NUM_FILES: int = 10000

FILE_SOURCES: typing.Dict[str, typing.Union['LocalFileSource', 'SudoFileSource']] = {
    # TODO: set up instrument and jupyterhub paths
}


class File(collections.namedtuple('File', ['id', 'object_id', 'user_id', 'original_file_name', 'utc_datetime'])):
    """
    This class provides an immutable wrapper around models.files.File.
    """

    def __new__(cls, id: int, object_id: int, user_id: int, original_file_name: str, utc_datetime: datetime.datetime=None):
        self = super(File, cls).__new__(cls, id, object_id, user_id, original_file_name, utc_datetime)
        return self

    @classmethod
    def from_database(cls, file: files.File) -> 'File':
        return File(id=file.id, object_id=file.object_id, user_id=file.user_id, original_file_name=file.original_file_name, utc_datetime=file.utc_datetime)

    @property
    def real_file_name(self) -> str:
        # ensure that 4 digits are enough for every valid file ID
        assert MAX_NUM_FILES <= 10000
        # TODO: make the base path configurable
        object = objects.get_object(self.object_id)
        action_id = object.action_id
        prefixed_file_name = '{file_id:04d}_{file_name}'.format(file_id=self.id, file_name=self.original_file_name)
        return os.path.join(FILE_STORAGE_PATH, str(action_id), str(self.object_id), prefixed_file_name)

    @property
    def uploader(self) -> users.User:
        return users.get_user(self.user_id)

    @property
    def title(self) -> typing.Union[str, None]:
        log_entry = FileLogEntry.query.filter_by(
            object_id=self.object_id,
            file_id=self.id,
            type=FileLogEntryType.EDIT_TITLE
        ).order_by(FileLogEntry.utc_datetime.desc()).first()
        if log_entry is None:
            return self.original_file_name
        return log_entry.data['title']

    @property
    def description(self) -> typing.Union[str, None]:
        log_entry = FileLogEntry.query.filter_by(
            object_id=self.object_id,
            file_id=self.id,
            type=FileLogEntryType.EDIT_DESCRIPTION
        ).order_by(FileLogEntry.utc_datetime.desc()).first()
        if log_entry is None:
            return None
        return log_entry.data['description']

    @property
    def log_entries(self):
        return FileLogEntry.query.filter_by(
            object_id=self.object_id,
            file_id=self.id
        ).order_by(FileLogEntry.utc_datetime.asc()).all()

    def open(self, read_only: bool=True) -> typing.BinaryIO:
        file_name = self.real_file_name
        if read_only:
            mode = 'rb'
        else:
            # before creating the file, the parent directories need exist
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            mode = 'xb'
        return open(file_name, mode)


def create_file(object_id: int, user_id: int, file_name: str, save_content: typing.Callable[[typing.BinaryIO], None]) -> None:
    """
    Creates a new file and adds it to the object and user logs. The function
    will call save_content with the opened file (in binary mode).

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param file_name: the original file name
    :param save_content: a function which will save the file's content to the
        given stream. The function will be called at most once.
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.FileNameTooLongError: when the file name is longer than 150
        bytes when encoded as UTF-8
    :raise errors.TooManyFilesForObjectError: when there are already 10000
        files for the object with the given id
    """
    # ensure that the object exists
    object = objects.get_object(object_id)
    # ensure that the user exists
    users.get_user(user_id)
    # ensure that the file name is valid
    if len(file_name.encode('utf8')) > 150:
        raise FileNameTooLongError()
    # ensure that the file can be stored
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
        original_file_name=file_name
    )
    db.session.add(db_file)
    db.session.commit()
    file = File.from_database(db_file)
    try:
        with file.open(read_only=False) as storage_file:
            save_content(storage_file)
    except:
        db.session.delete(db_file)
        db.session.commit()
        raise
    object_log.upload_file(user_id=user_id, object_id=object_id, file_id=file_id)
    user_log.upload_file(user_id=user_id, object_id=object_id, file_id=file_id)


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


def copy_file(object_id: int, user_id: int, file_source: str, file_name: str) -> None:
    """
    Creates a new file by copying the content of an existing file from a file_source.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param file_source: the file source name, a key in FILE_SOURCES
    :param file_name: the original file name
    :raise errors.InvalidFileSourceError: when no file source with the given
        name exists in FILE_SOURCES
    :raise FileNotFoundError: when no file with the given file_name exists for
        the given file source
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.FileNameTooLongError: when the file name is longer than 150
        bytes when encoded as UTF-8
    :raise errors.TooManyFilesForObjectError: when there are already 10000
        files for the object with the given id
    """
    file_source = _get_file_source(file_source)
    file_source.copy_file(object_id=object_id, user_id=user_id, file_name=file_name)


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


def get_existing_files_for_source(file_source: str, user_id: int, relative_path: str='', max_depth: int=None) -> typing.Dict:
    """
    Returns a file tree for the given file_source, relative_path and max_depth

    :param file_source: the file source name, a key in FILE_SOURCES
    :param max_depth: maximum depth of the returned file tree or None
    :return: a tree of dictionaries (for directories) and strings ('File' for
        files, 'Directory' for directories which would exceed max_depth)
    :raise errors.InvalidFileSourceError: when no file source with the given
        name exists in FILE_SOURCES
    """
    file_source = _get_file_source(file_source)
    return file_source.get_existing_files(user_id=user_id, relative_path=relative_path, max_depth=max_depth)


class LocalFileSource(object):
    """
    This class represents a file source providing files from a local,
    optionally user dependent directory.
    """
    def __init__(self, directory_function):
        self._directory_function = directory_function

    def copy_file(self, object_id: int, user_id: int, file_name: str) -> None:
        """
        Creates a new file by copying the content of an existing file from a file_source.

        :param object_id: the ID of an existing object
        :param user_id: the ID of an existing user
        :param file_name: the original file name
        :raise FileNotFoundError: when no file with the given file_name exists for
            the given file source
        :raise errors.ObjectDoesNotExistError: when no object with the given
            object ID exists
        :raise errors.UserDoesNotExistError: when no user with the given user ID
            exists
        :raise errors.FileNameTooLongError: when the file name is longer than 150
            bytes when encoded as UTF-8
        :raise errors.TooManyFilesForObjectError: when there are already 10000
            files for the object with the given id
        """
        source_stream = self._get_existing_file(user_id, file_name)
        save_content = lambda fdst, fsrc=source_stream: shutil.copyfileobj(fsrc, fdst)
        create_file(object_id, user_id, os.path.basename(file_name), save_content)
        pass

    def _get_existing_file(self, user_id, file_name) -> typing.BinaryIO:
        """
        Opens an existing file from a file source.

        :param user_id: the user ID, for user dependent file sources
        :param file_name: the original file name
        :return: an open read-only binary stream for the file
        :raise FileNotFoundError: when no file with the given file_name exists for
            the given file source
        """

        if file_name.startswith('/'):
            file_name = '.' + file_name
        existing_file_name = os.path.join(self._get_existing_file_path(user_id), file_name)
        return open(existing_file_name, 'rb')

    def _get_existing_file_path(self, user_id: int) -> str:
        """
        Returns the path in which the file source stores the existing files
        accessible by the given user.

        :param user_id: the user ID, for user dependent file sources
        :return: the path as string
        """
        return self._directory_function(user_id)

    def get_existing_files(self, user_id: int, relative_path: str='', max_depth: int=None) -> typing.Dict:
        """
        Returns a file tree for the given file_source, relative_path and max_depth.

        :param user_id: the user ID, for user dependent file sources
        :param relative_path: the path relative to the file source's base directory
        :param max_depth: maximum depth of the returned file tree or None
        :return: a tree of dictionaries (for directories) and strings ('File' for
            files, 'Directory' for directories which would exceed max_depth)
        :raise FileNotFoundError: when no directory with the given
            relative_path exists
        """

        def _path_depth(path):
            depth = itertools.count()
            while path not in ('/', '.', ''):
                path = os.path.dirname(path)
                next(depth)
            return next(depth)

        existing_file_path = os.path.realpath(self._get_existing_file_path(user_id))
        base_path = os.path.realpath(os.path.join(existing_file_path, relative_path))
        if os.path.commonprefix([existing_file_path, base_path]) != existing_file_path:
            raise FileNotFoundError('Path does not exist in the given file_source')

        file_tree = {}
        # file tree helper maps paths relative to base_path to paths relative to file_tree entries
        file_tree_helper = {'.': file_tree}

        for path, directories, files in os.walk(base_path, followlinks=True):
            relative_path = os.path.relpath(path, base_path)
            # prevent building a tree deeper than max_depth and insert placeholders instead
            depth = _path_depth(relative_path)

            for file in files:
                file_tree_helper[relative_path][file] = 'File'

            for directory in directories:
                if relative_path not in ('/', '.', ''):
                    directory_path = os.path.join(relative_path, directory)
                else:
                    directory_path = directory
                if max_depth is None or depth < max_depth:
                    file_tree_helper[directory_path] = file_tree_helper[relative_path][directory] = {}
                else:
                    file_tree_helper[directory_path] = file_tree_helper[relative_path][directory] = 'Directory'

            if max_depth is not None and depth >= max_depth:
                directories.clear()

        if file_tree == {} and not os.path.isdir(base_path):
            raise FileNotFoundError('Path does not exist in the given file_source')

        return file_tree


class SudoFileSource(object):
    """
    This class represents a local file source run as a different user.
    """
    def __init__(self, directory_function: typing.Callable[[int], str]):
        self._directory_function = directory_function

    def copy_file(self, object_id: int, user_id: int, file_name: str) -> None:
        """
        Creates a new file by copying the content of an existing file from a file_source.

        :param object_id: the ID of an existing object
        :param user_id: the ID of an existing user
        :param file_name: the original file name
        :raise FileNotFoundError: when no file with the given file_name exists for
            the given file source
        :raise errors.ObjectDoesNotExistError: when no object with the given
            object ID exists
        :raise errors.UserDoesNotExistError: when no user with the given user ID
            exists
        :raise errors.FileNameTooLongError: when the file name is longer than 150
            bytes when encoded as UTF-8
        :raise errors.TooManyFilesForObjectError: when there are already 10000
            files for the object with the given id
        """
        # ensure that the object exists
        object = objects.get_object(object_id)
        # ensure that the user exists
        users.get_user(user_id)
        # ensure that the file name is valid
        if len(file_name.encode('utf8')) > 150:
            raise FileNameTooLongError()

        # ensure that the other user can write to the storage path, by making
        # it accessible to all members of the sampledb group
        object = objects.get_object(object_id)
        action_id = object.action_id
        storage_path = os.path.join(FILE_STORAGE_PATH, str(action_id), str(object_id))
        os.makedirs(storage_path, exist_ok=True)
        os.chmod(storage_path, mode=stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)

        # TODO: handle non-ldap-users
        user_ldap_uid = get_user_ldap_uid(user_id)
        with tempfile.TemporaryFile() as fake_stdin:
            user_id = str(user_id)
            object_id = str(object_id)

            # TODO: get correct directory
            directory = '/Users/pgi-jcns-ta/rhiem/JupyterHub'
            b64_json_env = base64.b64encode(json.dumps(dict(os.environ)).encode('utf-8')).decode('utf-8')
            fake_stdin.write('\n'.join([sys.executable, b64_json_env, user_ldap_uid, user_id, object_id, directory, file_name, '']).encode('utf-8') )
            fake_stdin.seek(0)
            try:
                subprocess.check_output(['sudo', '/bin/bash', os.path.abspath('sampledb/scripts/sudo_file_source_copy_file.sh')], stdin=fake_stdin)
            except subprocess.CalledProcessError as e:
                # TODO: handle failure
                raise

    def get_existing_files(self, user_id: int, relative_path: str='', max_depth: int=None) -> typing.Dict:
        """
        Returns a file tree for the given file_source, relative_path and max_depth.

        :param user_id: the user ID, for user dependent file sources
        :param relative_path: the path relative to the file source's base directory
        :param max_depth: maximum depth of the returned file tree or None
        :return: a tree of dictionaries (for directories) and strings ('File' for
            files, 'Directory' for directories which would exceed max_depth)
        :raise FileNotFoundError: when no directory with the given
            relative_path exists
        """
        # directory = self._directory_function(user_id)
        user_ldap_uid = get_user_ldap_uid(user_id)
        posix_user, posix_group = get_posix_info(user_ldap_uid)
        directory = str(posix_group.description).split(':', 1)[-1] + '/' + user_ldap_uid + '/JupyterHub/'
        user_id = posix_user.uidNumber
        if not relative_path or relative_path == '/':
            relative_path = '.'

        with tempfile.TemporaryFile() as fake_stdin:
            user_id = str(user_id)
            max_depth = str(max_depth)
            fake_stdin.write('\n'.join([sys.executable, user_ldap_uid, user_id, directory, relative_path, max_depth, '']).encode('utf-8') )
            fake_stdin.seek(0)
            output = subprocess.check_output(['sudo', '/bin/bash', os.path.abspath('sampledb/scripts/sudo_file_source_get_existing_files.sh')], stdin=fake_stdin)
            try:
                file_tree = json.loads(output)
            except json.JSONDecodeError:
                return {}
            return file_tree


def _get_file_source(file_source: str) -> typing.Union[LocalFileSource, SudoFileSource]:
    """
    Returns the file source with the given name.

    :param file_source: the file source name, a key in FILE_SOURCES
    :return: the file source
    :raise errors.InvalidFileSourceError: when no path for file_source has not
        been defined in FILE_SOURCES
    """
    if file_source not in FILE_SOURCES.keys():
        raise InvalidFileSourceError("There is not file source named '{}'".format(file_source))
    return FILE_SOURCES[file_source]
