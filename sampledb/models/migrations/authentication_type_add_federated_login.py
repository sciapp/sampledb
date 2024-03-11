"""
ADD FEDERATED_LOGIN enum value to AuthenticationType enum.
"""

import os

import flask_sqlalchemy

from .utils import enum_value_migration

from .components_add_fed_login_available_column import MIGRATION_INDEX as PREVIOUS_INDEX

MIGRATION_INDEX = PREVIOUS_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    return enum_value_migration('authenticationtype', 'FEDERATED_LOGIN')
