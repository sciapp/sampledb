# coding: utf-8
"""
Add REMOTE_IMPORT_OBJECT enum value to FedObjectLogEntryType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('fedobjectlogentrytype', 'REMOTE_IMPORT_OBJECT')
