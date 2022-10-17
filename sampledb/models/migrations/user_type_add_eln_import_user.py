# coding: utf-8
"""
Add ELN_IMPORT_USER enum value to UserType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration
from .authentication_type_add_api_access_token import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('usertype', 'ELN_IMPORT_USER')
