# coding: utf-8
"""
Add CREATE_INSTRUMENT_LOG_ENTRY enum value to UserLogEntryType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration

MIGRATION_INDEX = 18
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('userlogentrytype', 'CREATE_INSTRUMENT_LOG_ENTRY')
