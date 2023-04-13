# coding: utf-8
"""
Add API_ACCESS_TOKEN enum value to AuthenticationType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration
from .instruments_add_show_linked_object_data import MIGRATION_INDEX as PREVIOUS_MIGRATION_INDEX

MIGRATION_INDEX = PREVIOUS_MIGRATION_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    return enum_value_migration('authenticationtype', 'API_ACCESS_TOKEN')
