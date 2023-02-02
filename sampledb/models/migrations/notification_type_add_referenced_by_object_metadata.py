# coding: utf-8
"""
Add REFERENCED_BY_OBJECT_METADATA enum value to NotificationType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration

MIGRATION_INDEX = 29
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('notificationtype', 'REFERENCED_BY_OBJECT_METADATA')
