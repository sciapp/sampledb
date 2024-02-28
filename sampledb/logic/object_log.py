# coding: utf-8
"""

"""

import datetime
import typing

import flask

from . import object_permissions, errors
from . import users
from .background_tasks.trigger_webhooks import post_trigger_object_log_webhooks
from .users import get_user
from ..models import ObjectLogEntry, ObjectLogEntryType, Permissions, Objects
from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def object_log_entry_to_json(log_entry: ObjectLogEntry) -> typing.Dict[str, typing.Any]:
    return {
        'log_entry_id': log_entry.id,
        'type': log_entry.type.name,
        'object_id': log_entry.object_id,
        'user_id': log_entry.user_id,
        'data': {key: value for key, value in log_entry.data.items() if key not in ['object', 'sample', 'measurement']},
        'utc_datetime': log_entry.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        'is_imported': log_entry.is_imported
    }


def get_object_log_entries_by_user(user_id: int, after_id: int = 0) -> typing.List[ObjectLogEntry]:
    user = get_user(user_id)
    if user.has_admin_permissions:
        object_log_entries = db.session.execute(db.select(ObjectLogEntry).where(ObjectLogEntry.id > after_id).order_by(db.desc(ObjectLogEntry.utc_datetime))).all()
    else:
        stmt = db.text("""
            SELECT DISTINCT object_id
            FROM user_object_permissions_by_all
            WHERE (user_id = :user_id OR user_id IS NULL) AND (requires_anonymous_users IS FALSE OR :enable_anonymous_users IS TRUE) AND (requires_instruments IS FALSE OR :enable_instruments IS TRUE)
        """).columns(
            Objects._current_table.c.object_id,
        ).subquery('readable_objects')
        stmt = db.select(ObjectLogEntry).join(stmt).where(ObjectLogEntry.id > after_id).order_by(db.desc(ObjectLogEntry.utc_datetime))

        object_log_entries = db.session.execute(stmt, {
            'user_id': user_id,
            'enable_anonymous_users': flask.current_app.config['ENABLE_ANONYMOUS_USERS'],
            'enable_instruments': not flask.current_app.config['DISABLE_INSTRUMENTS'],
            'after_id': after_id
        }).all()
    return process_object_log_entries([row[0] for row in object_log_entries], user_id)


def process_object_log_entries(object_log_entries: typing.List[ObjectLogEntry], user_id: typing.Optional[int] = None) -> typing.List[ObjectLogEntry]:
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
            object_id_value = object_log_entry.data.get(using_object_id)
            if type(object_id_value) is int:
                referenced_object_ids[object_log_entry.id] = object_id_value
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


def get_object_log_entry(object_log_entry_id: int, user_id: typing.Optional[int] = None) -> ObjectLogEntry:
    object_log_entry = ObjectLogEntry.query.filter_by(id=object_log_entry_id).order_by(db.desc(ObjectLogEntry.utc_datetime)).first()
    if object_log_entry is None:
        raise errors.ObjectLogEntryDoesNotExistError()
    return process_object_log_entries([object_log_entry], user_id)[0]


def get_object_log_entries(object_id: int, user_id: typing.Optional[int] = None) -> typing.List[ObjectLogEntry]:
    object_log_entries = ObjectLogEntry.query.filter_by(object_id=object_id).order_by(db.desc(ObjectLogEntry.utc_datetime)).all()
    return process_object_log_entries(object_log_entries, user_id)


def _store_new_log_entry(
        type: ObjectLogEntryType,
        object_id: int,
        user_id: int,
        data: typing.Dict[str, typing.Any],
        utc_datetime: typing.Optional[datetime.datetime] = None,
        is_imported: bool = False
) -> None:
    object_log_entry = ObjectLogEntry(
        type=type,
        object_id=object_id,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc) if utc_datetime is None else utc_datetime,
        is_imported=is_imported
    )
    db.session.add(object_log_entry)
    db.session.commit()
    post_trigger_object_log_webhooks(object_log_entry)


def create_object(
        user_id: int,
        object_id: int,
        previous_object_id: typing.Optional[int] = None,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        is_imported: bool = False
) -> None:
    data = {}
    if previous_object_id:
        data['previous_object_id'] = previous_object_id
    _store_new_log_entry(
        type=ObjectLogEntryType.CREATE_OBJECT,
        object_id=object_id,
        user_id=user_id,
        data=data,
        utc_datetime=utc_datetime,
        is_imported=is_imported
    )


def edit_object(
        user_id: int,
        object_id: int,
        version_id: int,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        is_imported: bool = False
) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.EDIT_OBJECT,
        object_id=object_id,
        user_id=user_id,
        data={
            'version_id': version_id
        },
        utc_datetime=utc_datetime,
        is_imported=is_imported
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


def post_comment(
        user_id: int,
        object_id: int,
        comment_id: int,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        is_imported: bool = False
) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.POST_COMMENT,
        object_id=object_id,
        user_id=user_id,
        data={
            'comment_id': comment_id
        },
        utc_datetime=utc_datetime,
        is_imported=is_imported
    )


def upload_file(
        user_id: int,
        object_id: int,
        file_id: int,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        is_imported: bool = False
) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.UPLOAD_FILE,
        object_id=object_id,
        user_id=user_id,
        data={
            'file_id': file_id
        },
        utc_datetime=utc_datetime,
        is_imported=is_imported
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


def assign_location(
        user_id: int,
        object_id: int,
        object_location_assignment_id: int,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        is_imported: bool = False
) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.ASSIGN_LOCATION,
        object_id=object_id,
        user_id=user_id,
        data={
            'object_location_assignment_id': object_location_assignment_id
        },
        utc_datetime=utc_datetime,
        is_imported=is_imported
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


def import_from_eln_file(user_id: int, object_id: int) -> None:
    _store_new_log_entry(
        type=ObjectLogEntryType.IMPORT_FROM_ELN_FILE,
        object_id=object_id,
        user_id=user_id,
        data={}
    )
