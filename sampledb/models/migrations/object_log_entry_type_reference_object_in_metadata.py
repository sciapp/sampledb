# coding: utf-8
"""
Add REFERENCE_OBJECT_IN_METADATA enum value to ObjectLogEntryType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('objectlogentrytype', 'REFERENCE_OBJECT_IN_METADATA')
