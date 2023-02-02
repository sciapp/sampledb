# coding: utf-8
"""
Add REMOTE_IMPORT_OBJECT enum value to FedObjectLogEntryType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration

MIGRATION_INDEX = 137
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('fedobjectlogentrytype', 'REMOTE_IMPORT_OBJECT')
