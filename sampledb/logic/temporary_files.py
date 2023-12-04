import dataclasses
import datetime
import typing
import flask

from ..models import temporary_files
from .. import db
from .files import create_database_file


@dataclasses.dataclass(frozen=True)
class TemporaryFile:
    """
    This class provides an immutable wrapper around models.temporary_files.TemporaryFile.
    """
    id: int
    context_id: str
    file_name: str
    user_id: int
    utc_datetime: datetime.datetime
    binary_data: bytes

    @classmethod
    def from_database(cls, temporary_file: temporary_files.TemporaryFile) -> 'TemporaryFile':
        return TemporaryFile(
            id=temporary_file.id,
            context_id=temporary_file.context_id,
            file_name=temporary_file.file_name,
            user_id=temporary_file.user_id,
            utc_datetime=temporary_file.utc_datetime,
            binary_data=temporary_file.binary_data
        )


def get_files_for_context_id(context_id: str) -> typing.List[TemporaryFile]:
    """
    Get all temporary files saved in a given context.

    :param context_id: the context ID for which to return all temporary files
    """
    return [
        TemporaryFile.from_database(temporary_file)
        for temporary_file in temporary_files.TemporaryFile.query.filter_by(context_id=context_id).order_by(db.asc(temporary_files.TemporaryFile.id)).all()
    ]


def delete_expired_temporary_files() -> None:
    """
    Delete all expired temporary files.
    """
    time_limit = flask.current_app.config['TEMPORARY_FILE_TIME_LIMIT']
    db.session.query(temporary_files.TemporaryFile).filter(
        temporary_files.TemporaryFile.utc_datetime < datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=time_limit)
    ).delete()
    db.session.commit()


def delete_temporary_files(
        context_id: str
) -> None:
    """
    Delete all temporary files saved in a given context.

    :param context_id: the context ID for which to delete all temporary files
    """
    db.session.query(temporary_files.TemporaryFile).filter(
        temporary_files.TemporaryFile.context_id == context_id
    ).delete()
    db.session.commit()


def create_temporary_file(
        context_id: str,
        file_name: str,
        user_id: int,
        binary_data: bytes
) -> TemporaryFile:
    """
    Create a temporary file.

    :param context_id: the context ID for the temporary file
    :param file_name: the name for the file
    :param user_id: the ID of the user who uploaded the file
    :param binary_data: the data for the file
    :return: the created file
    """
    temporary_file = temporary_files.TemporaryFile(
        context_id=context_id,
        file_name=file_name,
        user_id=user_id,
        binary_data=binary_data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(temporary_file)
    db.session.commit()
    return TemporaryFile.from_database(temporary_file)


def copy_temporary_files(
        file_ids: typing.Sequence[int],
        context_id: str,
        user_id: int,
        object_ids: typing.Sequence[int]
) -> typing.Dict[int, int]:
    """
    Copy a list of temporary files to one or more objects.

    :param file_ids: the IDs of existing temporary files
    :param context_id: the context ID for the temporary files
    :param user_id: the ID of the user copying the files
    :param object_ids: the IDs of objects to copy the files to
    :return: a mapping between temporary and permanent file IDs
    """
    temporary_file_id_map = {}
    temporary_files = get_files_for_context_id(context_id=context_id)
    for file in temporary_files:
        if file.id in file_ids:
            def save_content(stream: typing.BinaryIO, file: TemporaryFile = file) -> None:
                stream.write(file.binary_data)
            for object_id in object_ids:
                temporary_file_id_map[file.id] = create_database_file(
                    object_id=object_id,
                    user_id=user_id,
                    file_name=file.file_name,
                    save_content=save_content
                ).id
    return temporary_file_id_map


def replace_file_reference_ids(
        data: typing.Any,
        temporary_file_id_map: typing.Dict[int, int]
) -> None:
    if isinstance(data, dict):
        if '_type' in data:
            if data['_type'] == 'file':
                if -data['file_id'] in temporary_file_id_map:
                    data['file_id'] = temporary_file_id_map[-data['file_id']]
        else:
            for property_data in data.values():
                replace_file_reference_ids(property_data, temporary_file_id_map)
    if isinstance(data, list):
        for item_data in data:
            replace_file_reference_ids(item_data, temporary_file_id_map)


def get_referenced_temporary_file_ids(
        data: typing.Any
) -> typing.Set[int]:
    refrenced_file_ids = set()
    if isinstance(data, dict):
        if '_type' in data:
            if data['_type'] == 'file' and data['file_id'] < 0:
                refrenced_file_ids.add(-data['file_id'])
        else:
            for property_data in data.values():
                refrenced_file_ids = refrenced_file_ids.union(get_referenced_temporary_file_ids(property_data))
    if isinstance(data, list):
        for item_data in data:
            refrenced_file_ids = refrenced_file_ids.union(get_referenced_temporary_file_ids(item_data))
    return refrenced_file_ids
