# coding: utf-8
"""
Add OBJECT_PERMISSIONS enum value to WebhookType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('webhooktype', 'OBJECT_PERMISSIONS')
