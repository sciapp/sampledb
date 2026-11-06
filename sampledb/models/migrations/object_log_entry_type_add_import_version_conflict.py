"""
Add IMPORT_CONFLICTING_VERSION enum value to FedObjectLogEntryType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration("objectlogentrytype", "IMPORT_CONFLICTING_VERSION")
