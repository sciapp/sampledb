# coding: utf-8
"""
Add EDIT_URL enum value to FileLogEntryType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('filelogentrytype', 'EDIT_URL')
