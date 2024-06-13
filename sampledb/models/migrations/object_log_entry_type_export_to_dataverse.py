# coding: utf-8
"""
Add EXPORT_TO_DATAVERSE enum value to ObjectLogEntryType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('objectlogentrytype', 'EXPORT_TO_DATAVERSE')
