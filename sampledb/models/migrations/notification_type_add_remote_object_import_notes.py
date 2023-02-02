# coding: utf-8
"""
Add REMOTE_OBJECT_IMPORT_NOTES enum value to NotificationType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration

MIGRATION_INDEX = 140
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('notificationtype', 'REMOTE_OBJECT_IMPORT_NOTES')
