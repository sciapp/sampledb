# coding: utf-8
"""

"""

import datetime
import typing

from . import object_permissions
from . import users
from ..models import ObjectLogEntry, ObjectLogEntryType, Permissions
from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def get_object_log_entries(object_id: int, user_id: typing.Optional[int] = None) -> typing.List[ObjectLogEntry]:
    object_log_entries = ObjectLogEntry.query.filter_by(object_id=object_id).order_by(db.desc(ObjectLogEntry.utc_datetime)).all()
    processed_object_log_entries = []
    users_by_id: typing.Dict[typing.Optional[int], typing.Optional[users.User]] = {None: None}
    referenced_object_ids = {}
    referenced_object_type_by_log_entry_type = {
        ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT: 'measurement',
        ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION: 'sample',
        ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA: 'object'
    }
    for object_log_entry in object_log_entries:
        using_object_type = referenced_object_type_by_log_entry_type.get(object_log_entry.type)
        if using_object_type is not None:
            using_object_id = using_object_type + '_id'
            object_id = object_log_entry.data.get(using_object_id)
            if object_id is None:
                # object ID was not set or has already been cleared
                pass
            else:
                referenced_object_ids[object_log_entry.id] = object_id
        if object_log_entry.user_id not in users_by_id:
            users_by_id[object_log_entry.user_id] = users.get_user(object_log_entry.user_id)
        object_log_entry.user = users_by_id[object_log_entry.user_id]
        # remove the modified log entry from the session to avoid an
        # accidental commit of these changes
        db.session.expunge(object_log_entry)
        processed_object_log_entries.append(object_log_entry)
    if referenced_object_ids:
        referenced_objects = object_permissions.get_objects_with_permissions(
            user_id=user_id,
            permissions=Permissions.READ,
            object_ids=list(set(referenced_object_ids.values()))
        )
        referenced_objects_by_id = {
            object.id: object
            for object in referenced_objects
        }
        for object_log_entry in processed_object_log_entries:
            if object_log_entry.id in referenced_object_ids:
                using_object_type = referenced_object_type_by_log_entry_type[object_log_entry.type]
                using_object_id = using_object_type + '_id'
                referenced_object_id = referenced_object_ids[object_log_entry.id]
                if referenced_object_id in referenced_objects_by_id:
                    referenced_object = referenced_objects_by_id[referenced_object_id]
                    object_log_entry.data[using_object_type] = referenced_object
                else:
                    # Clear the using object ID, the user may only know that the
                    # object was used for some other object, but not for which
                    object_log_entry.data[using_object_id] = None
    return processed_object_log_entries


def _store_new_log_entry(type: ObjectLogEntryType, object_id: int, user_id: int, data: typing.Dict[str, typing.Any]) -> None:
    object_log_entry = ObjectLogEntry(
        type=type,
        object_id=object_id,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.utcnow()
    )
    db.session.add(object_log_entry)
    db.session.commit()


def create_object(user_id: int, object_id: int, previous_object_id: typing.Optional[int] = None) -> None:
    data = {}
    if previous_object_id:
        data['previous_object_id'] = previous_object_id
    _store_new_log_entry(
        type=ObjectLogEntryType.CREATE_OBJECT,
        object_id=object_id,
        user_id=user_id,
        data=data
    )


def edit_object(user_id: int, object_id: int, version_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.EDIT_OBJECT,
        object_id=object_id,
        user_id=user_id,
        data={
            'version_id': version_id
        }
    )


def restore_object_version(user_id: int, object_id: int, version_id: int, restored_version_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.RESTORE_OBJECT_VERSION,
        object_id=object_id,
        user_id=user_id,
        data={
            'version_id': version_id,
            'restored_version_id': restored_version_id
        }
    )


def use_object_in_measurement(user_id: int, object_id: int, measurement_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT,
        object_id=object_id,
        user_id=user_id,
        data={
            'measurement_id': measurement_id
        }
    )


def use_object_in_sample(user_id: int, object_id: int, sample_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION,
        object_id=object_id,
        user_id=user_id,
        data={
            'sample_id': sample_id
        }
    )


def post_comment(user_id: int, object_id: int, comment_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.POST_COMMENT,
        object_id=object_id,
        user_id=user_id,
        data={
            'comment_id': comment_id
        }
    )


def upload_file(user_id: int, object_id: int, file_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.UPLOAD_FILE,
        object_id=object_id,
        user_id=user_id,
        data={
            'file_id': file_id
        }
    )


def create_batch(user_id: int, object_id: int, batch_object_ids: typing.List[int]) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.CREATE_BATCH,
        object_id=object_id,
        user_id=user_id,
        data={
            'object_ids': batch_object_ids
        }
    )


def assign_location(user_id: int, object_id: int, object_location_assignment_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.ASSIGN_LOCATION,
        object_id=object_id,
        user_id=user_id,
        data={
            'object_location_assignment_id': object_location_assignment_id
        }
    )


def link_publication(
        user_id: int,
        object_id: int,
        doi: str,
        title: typing.Optional[str] = None,
        object_name: typing.Optional[str] = None
) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.LINK_PUBLICATION,
        object_id=object_id,
        user_id=user_id,
        data={
            'doi': doi,
            'title': title,
            'object_name': object_name
        }
    )


def reference_object_in_metadata(user_id: int, object_id: int, referencing_object_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA,
        object_id=object_id,
        user_id=user_id,
        data={
            'object_id': referencing_object_id
        }
    )


def export_to_dataverse(user_id: int, object_id: int, dataverse_url: str) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.EXPORT_TO_DATAVERSE,
        object_id=object_id,
        user_id=user_id,
        data={
            'dataverse_url': dataverse_url
        }
    )


def link_project(user_id: int, object_id: int, project_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.LINK_PROJECT,
        object_id=object_id,
        user_id=user_id,
        data={
            'project_id': project_id
        }
    )


def unlink_project(user_id: int, object_id: int, project_id: int, project_deleted: bool = False) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.UNLINK_PROJECT,
        object_id=object_id,
        user_id=user_id,
        data={
            'project_id': project_id,
            'project_deleted': project_deleted
        }
    )
