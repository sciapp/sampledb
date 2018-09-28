# coding: utf-8
"""

"""

import datetime
import typing
from .errors import ObjectDoesNotExistError
from .users import get_user
from .permissions import get_user_object_permissions, Permissions
from ..models import UserLogEntry, UserLogEntryType
from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def get_user_log_entries(user_id: int, as_user_id: typing.Optional[int]=None) -> typing.List[UserLogEntry]:
    user_log_entries = UserLogEntry.query.filter_by(user_id=user_id).order_by(db.desc(UserLogEntry.utc_datetime)).all()
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


def _store_new_log_entry(type: UserLogEntryType, user_id: int, data: dict):
    user_log_entry = UserLogEntry(
        type=type,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.utcnow()
    )
    db.session.add(user_log_entry)
    db.session.commit()


def create_object(user_id: int, object_id: int):
    _store_new_log_entry(
        type=UserLogEntryType.CREATE_OBJECT,
        user_id=user_id,
        data={
            'object_id': object_id
        }
    )


def edit_object(user_id: int, object_id: int, version_id: int):
    _store_new_log_entry(
        type=UserLogEntryType.EDIT_OBJECT,
        user_id=user_id,
        data={
            'object_id': object_id,
            'version_id': version_id
        }
    )


def restore_object_version(user_id: int, object_id: int, version_id: int, restored_version_id: int):
    _store_new_log_entry(
        type=UserLogEntryType.RESTORE_OBJECT_VERSION,
        user_id=user_id,
        data={
            'object_id': object_id,
            'version_id': version_id,
            'restored_version_id': restored_version_id
        }
    )


def edit_object_permissions(user_id: int, object_id: int):
    _store_new_log_entry(
        type=UserLogEntryType.EDIT_OBJECT_PERMISSIONS,
        user_id=user_id,
        data={
            'object_id': object_id
        }
    )


def register_user(user_id: int, email: str):
    _store_new_log_entry(
        type=UserLogEntryType.REGISTER_USER,
        user_id=user_id,
        data={
            'email': email
        }
    )


def invite_user(user_id: int, email: str):
    _store_new_log_entry(
        type=UserLogEntryType.INVITE_USER,
        user_id=user_id,
        data={
            'email': email
        }
    )


def edit_user_preferences(user_id: int):
    _store_new_log_entry(
        type=UserLogEntryType.EDIT_USER_PREFERENCES,
        user_id=user_id,
        data={}
    )


def post_comment(user_id: int, object_id: int, comment_id: int):
    _store_new_log_entry(
        type=UserLogEntryType.POST_COMMENT,
        user_id=user_id,
        data={
            'object_id': object_id,
            'comment_id': comment_id
        }
    )


def upload_file(user_id: int, object_id: int, file_id: int):
    _store_new_log_entry(
        type=UserLogEntryType.UPLOAD_FILE,
        user_id=user_id,
        data={
            'object_id': object_id,
            'file_id': file_id
        }
    )


def create_batch(user_id: int, batch_object_ids: typing.List[int]):
    _store_new_log_entry(
        type=UserLogEntryType.CREATE_BATCH,
        user_id=user_id,
        data={
            'object_ids': batch_object_ids
        }
    )
