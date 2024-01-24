import os

import flask_sqlalchemy

from .action_type_add_show_in_object_filters import MIGRATION_INDEX as PREVIOUS_INDEX
from .utils import enum_value_migration

MIGRATION_INDEX = PREVIOUS_INDEX + 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    return enum_value_migration('notificationtype', 'AUTOMATIC_USER_FEDERATION')
