"""
ADD FEDERATED_LOGIN enum value to AuthenticationType enum.
"""

import flask_sqlalchemy

from .utils import enum_value_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    return enum_value_migration('authenticationtype', 'FEDERATED_LOGIN')
