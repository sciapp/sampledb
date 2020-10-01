# coding: utf-8
"""
Replace the type column by the type_id column in the actions table.
"""

import os

from ..actions import ActionType

MIGRATION_INDEX = 31
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'actions'
    """).fetchall()
    if ('type_id',) in column_names:
        return False

    # Perform migration
    db.session.execute("""
        ALTER TABLE actions
        ADD type_id INTEGER NULL
    """)

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
        db.session.execute("""
            UPDATE actions
            SET type_id = :type_id
            WHERE type::text = :type
        """, params=action_type)

    db.session.execute("""
        ALTER TABLE actions
        ALTER type_id SET NOT NULL
    """)

    db.session.execute("""
        ALTER TABLE actions
        ADD CONSTRAINT fk_actions_type_id FOREIGN KEY (type_id) REFERENCES action_types (id)
    """)

    db.session.execute("""
        ALTER TABLE actions
        DROP type
    """)
    return True
