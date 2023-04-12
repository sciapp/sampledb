# coding: utf-8
"""
Add API_TOKEN enum value to AuthenticationType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration

MIGRATION_INDEX = 14
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    return enum_value_migration('authenticationtype', 'API_TOKEN')
