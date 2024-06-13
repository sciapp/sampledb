# coding: utf-8
"""
Add ASSIGN_LOCATION enum value to UserLogEntryType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('userlogentrytype', 'ASSIGN_LOCATION')
