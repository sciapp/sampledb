# coding: utf-8
"""

"""

import datetime
import typing
from ..models import UserLogEntry, UserLogEntryType
from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def get_user_log_entries(user_id: int) -> typing.List[UserLogEntry]:
    return UserLogEntry.query.filter_by(user_id=user_id).order_by(db.desc(UserLogEntry.utc_datetime)).all()


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
