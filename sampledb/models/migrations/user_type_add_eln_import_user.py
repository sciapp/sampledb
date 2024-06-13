# coding: utf-8
"""
Add ELN_IMPORT_USER enum value to UserType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('usertype', 'ELN_IMPORT_USER')
