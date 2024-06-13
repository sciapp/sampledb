# coding: utf-8
"""
Add REMOTE_OBJECT_IMPORT_NOTES enum value to NotificationType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('notificationtype', 'REMOTE_OBJECT_IMPORT_NOTES')
