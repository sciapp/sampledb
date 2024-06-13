# coding: utf-8
"""
Add RESPONSIBILITY_ASSIGNMENT_DECLINED enum value to NotificationType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('notificationtype', 'RESPONSIBILITY_ASSIGNMENT_DECLINED')
