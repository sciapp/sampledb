# coding: utf-8
"""
Add FEDERATION_USER enum value to UserType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration

MIGRATION_INDEX = 78
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('usertype', 'FEDERATION_USER')
