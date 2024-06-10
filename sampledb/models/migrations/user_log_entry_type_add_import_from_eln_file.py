# coding: utf-8
"""
Add IMPORT_FROM_ELN_FILE enum value to UserLogEntryType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('userlogentrytype', 'IMPORT_FROM_ELN_FILE')
