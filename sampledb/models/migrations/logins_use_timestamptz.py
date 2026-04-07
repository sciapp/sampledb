# coding: utf-8
"""
In the logins table, replace columns of type TIMESTAMP WITHOUT TIME ZONE with
columns of type TIMESTAMP WITH TIME ZONE, using UTC for the conversion.
"""

import flask_sqlalchemy

from .utils import timestamp_add_timezone_utc_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    migrations_ran = [
        timestamp_add_timezone_utc_migration(table_name, column_name)
        for table_name, column_name in [
            ('logins', 'created_at'),
            ('logins', 'expires_at'),
        ]
    ]
    return any(migrations_ran)
