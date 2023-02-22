# coding: utf-8
"""
Add ASSIGN_LOCATION enum value to ObjectLogEntryType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration

MIGRATION_INDEX = 2
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('objectlogentrytype', 'ASSIGN_LOCATION')
