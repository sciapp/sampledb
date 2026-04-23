"""
Add CREATE_VERSION_CONFLICT and SOLVE_VERSION_CONFLICT enum value to FedObjectLogEntryType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return (
        enum_value_migration("fedobjectlogentrytype", "CREATE_VERSION_CONFLICT") and
        enum_value_migration("fedobjectlogentrytype", "SOLVE_VERSION_CONFLICT")
    )
