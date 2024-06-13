# coding: utf-8
"""
Add INSTRUMENT_LOG_ENTRY_CREATED enum value to NotificationType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('notificationtype', 'INSTRUMENT_LOG_ENTRY_CREATED')
