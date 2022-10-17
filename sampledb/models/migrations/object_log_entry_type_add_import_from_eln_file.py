# coding: utf-8
"""
Add IMPORT_FROM_ELN_FILE enum value to ObjectLogEntryType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration
from .user_type_add_eln_import_user import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('objectlogentrytype', 'IMPORT_FROM_ELN_FILE')
