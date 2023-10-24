# coding: utf-8
"""

"""

import datetime
import typing
from .errors import ObjectDoesNotExistError
from .users import get_user
from .object_permissions import get_user_object_permissions
from ..models import UserLogEntry, UserLogEntryType, ObjectLocationAssignment, Permissions
from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def get_user_log_entries(user_id: int, as_user_id: typing.Optional[int] = None) -> typing.List[UserLogEntry]:
    user_log_entries: typing.List[UserLogEntry] = UserLogEntry.query.filter_by(user_id=user_id).order_by(db.desc(UserLogEntry.utc_datetime)).all()
    if as_user_id is None or as_user_id == user_id or get_user(as_user_id).is_admin:
        return user_log_entries
    visible_user_log_entries = []
    for user_log_entry in user_log_entries:
        if 'object_id' in user_log_entry.data:
            object_id = user_log_entry.data['object_id']
            try:
                if Permissions.READ in get_user_object_permissions(user_id=as_user_id, object_id=object_id):
                    visible_user_log_entries.append(user_log_entry)
            except ObjectDoesNotExistError:
                pass
        elif 'object_ids' in user_log_entry.data:
            object_ids = user_log_entry.data['object_ids']
            for object_id in object_ids:
                try:
                    if Permissions.READ in get_user_object_permissions(user_id=as_user_id, object_id=object_id):
                        visible_user_log_entries.append(user_log_entry)
                        break
                except ObjectDoesNotExistError:
                    pass
    return visible_user_log_entries


def get_user_related_object_ids(user_id: int) -> typing.Set[int]:
    """
    Return a set of IDs of all objects related to a given user.

    :param user_id: the ID of an existing user
    :return: a set of object IDs related to the user
    """
    user_log_entries = UserLogEntry.query.filter_by(user_id=user_id).all()
    user_related_object_ids = set()
    object_location_assignment_ids = set()
    for user_log_entry in user_log_entries:
        if 'object_id' in user_log_entry.data:
            user_related_object_ids.add(user_log_entry.data['object_id'])
        elif 'object_ids' in user_log_entry.data:
            user_related_object_ids.update(set(user_log_entry.data['object_ids']))
        elif 'object_location_assignment_id' in user_log_entry.data:
            object_location_assignment_ids.add(user_log_entry.data['object_location_assignment_id'])
    if object_location_assignment_ids:
        object_location_assignment_object_ids_result = db.session.query(
            ObjectLocationAssignment.object_id
        ).filter(
            ObjectLocationAssignment.id.in_(object_location_assignment_ids)
        ).distinct().all()
        object_location_assignment_object_ids = set(
            object_location_assignment_object_id[0]
            for object_location_assignment_object_id in object_location_assignment_object_ids_result
        )
        user_related_object_ids.update(object_location_assignment_object_ids)
    return user_related_object_ids


def _store_new_log_entry(type: UserLogEntryType, user_id: int, data: typing.Dict[str, typing.Any]) -> None:
    user_log_entry = UserLogEntry(
        type=type,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(user_log_entry)
    db.session.commit()


def create_object(user_id: int, object_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.CREATE_OBJECT,
        user_id=user_id,
        data={
            'object_id': object_id
        }
    )


def edit_object(user_id: int, object_id: int, version_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.EDIT_OBJECT,
        user_id=user_id,
        data={
            'object_id': object_id,
            'version_id': version_id
        }
    )


def restore_object_version(user_id: int, object_id: int, version_id: int, restored_version_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.RESTORE_OBJECT_VERSION,
        user_id=user_id,
        data={
            'object_id': object_id,
            'version_id': version_id,
            'restored_version_id': restored_version_id
        }
    )


def edit_object_permissions(user_id: int, object_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.EDIT_OBJECT_PERMISSIONS,
        user_id=user_id,
        data={
            'object_id': object_id
        }
    )


def register_user(user_id: int, email: str) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.REGISTER_USER,
        user_id=user_id,
        data={
            'email': email
        }
    )


def invite_user(user_id: int, email: str) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.INVITE_USER,
        user_id=user_id,
        data={
            'email': email
        }
    )


def edit_user_preferences(user_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.EDIT_USER_PREFERENCES,
        user_id=user_id,
        data={}
    )


def post_comment(user_id: int, object_id: int, comment_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.POST_COMMENT,
        user_id=user_id,
        data={
            'object_id': object_id,
            'comment_id': comment_id
        }
    )


def upload_file(user_id: int, object_id: int, file_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.UPLOAD_FILE,
        user_id=user_id,
        data={
            'object_id': object_id,
            'file_id': file_id
        }
    )


def create_batch(user_id: int, batch_object_ids: typing.List[int]) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.CREATE_BATCH,
        user_id=user_id,
        data={
            'object_ids': batch_object_ids
        }
    )


def assign_location(user_id: int, object_location_assignment_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.ASSIGN_LOCATION,
        user_id=user_id,
        data={
            'object_location_assignment_id': object_location_assignment_id
        }
    )


def create_location(user_id: int, location_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.CREATE_LOCATION,
        user_id=user_id,
        data={
            'location_id': location_id
        }
    )


def update_location(user_id: int, location_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.UPDATE_LOCATION,
        user_id=user_id,
        data={
            'location_id': location_id
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
        type=UserLogEntryType.LINK_PUBLICATION,
        user_id=user_id,
        data={
            'object_id': object_id,
            'doi': doi,
            'title': title,
            'object_name': object_name
        }
    )


def create_instrument_log_entry(user_id: int, instrument_id: int, instrument_log_entry_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.CREATE_INSTRUMENT_LOG_ENTRY,
        user_id=user_id,
        data={
            'instrument_id': instrument_id,
            'instrument_log_entry_id': instrument_log_entry_id
        }
    )


def import_from_eln_file(user_id: int, object_id: int) -> None:
    _store_new_log_entry(
        type=UserLogEntryType.IMPORT_FROM_ELN_FILE,
        user_id=user_id,
        data={
            'object_id': object_id
        }
    )
