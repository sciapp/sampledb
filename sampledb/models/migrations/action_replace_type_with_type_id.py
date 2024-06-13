# coding: utf-8
"""
Replace the type column by the type_id column in the actions table.
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..actions import ActionType


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('actions', 'type_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD type_id INTEGER NULL
    """))

    default_action_types = [
        {
            'type_id': ActionType.SAMPLE_CREATION,
            'type': 'SAMPLE_CREATION'
        },
        {
            'type_id': ActionType.MEASUREMENT,
            'type': 'MEASUREMENT'
        },
        {
            'type_id': ActionType.SIMULATION,
            'type': 'SIMULATION',
        }
    ]
    for action_type in default_action_types:
        db.session.execute(db.text("""
            UPDATE actions
            SET type_id = :type_id
            WHERE type::text = :type
        """), params=action_type)

    db.session.execute(db.text("""
        ALTER TABLE actions
        ALTER type_id SET NOT NULL
    """))

    db.session.execute(db.text("""
        ALTER TABLE actions
        ADD CONSTRAINT fk_actions_type_id FOREIGN KEY (type_id) REFERENCES action_types (id)
    """))

    db.session.execute(db.text("""
        ALTER TABLE actions
        DROP type
    """))
    return True
