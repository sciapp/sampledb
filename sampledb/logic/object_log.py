# coding: utf-8
"""

"""

import datetime
import typing

from . import objects
from . import object_permissions
from ..models import ObjectLogEntry, ObjectLogEntryType, Permissions
from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def get_object_log_entries(object_id: int, user_id: typing.Optional[int] = None) -> typing.List[ObjectLogEntry]:
    object_log_entries = ObjectLogEntry.query.filter_by(object_id=object_id).order_by(db.desc(ObjectLogEntry.utc_datetime)).all()
    processed_object_log_entries = []
    for object_log_entry in object_log_entries:
        use_object_entry = False
        using_object_type = ''
        if object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT:
            use_object_entry = True
            using_object_type = 'measurement'
        elif object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION:
            use_object_entry = True
            using_object_type = 'sample'
        elif object_log_entry.type == ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA:
            use_object_entry = True
            using_object_type = 'object'
        if use_object_entry:
            using_object_id = using_object_type + '_id'
            object_id = object_log_entry.data[using_object_id]
            object = objects.get_object(object_id=object_id)
            if user_id is not None and Permissions.READ not in object_permissions.get_user_object_permissions(object_id=object_id, user_id=user_id):
                # Clear the using object ID, the user may only know that the
                # object was used for some other object, but not for which
                object_log_entry.data[using_object_id] = None
            else:
                object_log_entry.data[using_object_type] = object

        processed_object_log_entries.append(object_log_entry)
    return processed_object_log_entries


def _store_new_log_entry(type: ObjectLogEntryType, object_id: int, user_id: int, data: dict):
    object_log_entry = ObjectLogEntry(
        type=type,
        object_id=object_id,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.utcnow()
    )
    db.session.add(object_log_entry)
    db.session.commit()


def create_object(user_id: int, object_id: int, previous_object_id: typing.Optional[int] = None):
    data = {}
    if previous_object_id:
        data['previous_object_id'] = previous_object_id
    _store_new_log_entry(
        type=ObjectLogEntryType.CREATE_OBJECT,
        object_id=object_id,
        user_id=user_id,
        data=data
    )


def edit_object(user_id: int, object_id: int, version_id: int):
    _store_new_log_entry(
        type=ObjectLogEntryType.EDIT_OBJECT,
        object_id=object_id,
        user_id=user_id,
        data={
            'version_id': version_id
        }
    )


def restore_object_version(user_id: int, object_id: int, version_id: int, restored_version_id: int):
    _store_new_log_entry(
        type=ObjectLogEntryType.RESTORE_OBJECT_VERSION,
        object_id=object_id,
        user_id=user_id,
        data={
            'version_id': version_id,
            'restored_version_id': restored_version_id
        }
    )


def use_object_in_measurement(user_id: int, object_id: int, measurement_id: int):
    _store_new_log_entry(
        type=ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT,
        object_id=object_id,
        user_id=user_id,
        data={
            'measurement_id': measurement_id
        }
    )


def use_object_in_sample(user_id: int, object_id: int, sample_id: int):
    _store_new_log_entry(
        type=ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION,
        object_id=object_id,
        user_id=user_id,
        data={
            'sample_id': sample_id
        }
    )


def post_comment(user_id: int, object_id: int, comment_id: int):
    _store_new_log_entry(
        type=ObjectLogEntryType.POST_COMMENT,
        object_id=object_id,
        user_id=user_id,
        data={
            'comment_id': comment_id
        }
    )


def upload_file(user_id: int, object_id: int, file_id: int):
    _store_new_log_entry(
        type=ObjectLogEntryType.UPLOAD_FILE,
        object_id=object_id,
        user_id=user_id,
        data={
            'file_id': file_id
        }
    )


def create_batch(user_id: int, object_id: int, batch_object_ids: typing.List[int]):
    _store_new_log_entry(
        type=ObjectLogEntryType.CREATE_BATCH,
        object_id=object_id,
        user_id=user_id,
        data={
            'object_ids': batch_object_ids
        }
    )


def assign_location(user_id: int, object_id: int, object_location_assignment_id: int):
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
):
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


def reference_object_in_metadata(user_id: int, object_id: int, referencing_object_id: int):
    _store_new_log_entry(
        type=ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA,
        object_id=object_id,
        user_id=user_id,
        data={
            'object_id': referencing_object_id
        }
    )


def export_to_dataverse(user_id: int, object_id: int, dataverse_url: str):
    _store_new_log_entry(
        type=ObjectLogEntryType.EXPORT_TO_DATAVERSE,
        object_id=object_id,
        user_id=user_id,
        data={
            'dataverse_url': dataverse_url
        }
    )


def link_project(user_id: int, object_id: int, project_id: int):
    _store_new_log_entry(
        type=ObjectLogEntryType.LINK_PROJECT,
        object_id=object_id,
        user_id=user_id,
        data={
            'project_id': project_id
        }
    )


def unlink_project(user_id: int, object_id: int, project_id: int, project_deleted: bool = False):
    _store_new_log_entry(
        type=ObjectLogEntryType.UNLINK_PROJECT,
        object_id=object_id,
        user_id=user_id,
        data={
            'project_id': project_id,
            'project_deleted': project_deleted
        }
    )
