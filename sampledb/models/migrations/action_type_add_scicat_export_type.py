# coding: utf-8
"""
Add the scicat_export_type column to the action_types table.
"""

import os

import flask_sqlalchemy

from ..actions import ActionType

MIGRATION_INDEX = 110
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Add column to action_type table
    client_column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'action_types'
    """)).fetchall()
    if ('scicat_export_type',) in client_column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE action_types
        ADD scicat_export_type scicatexporttype
    """))

    scicat_export_types = {
        ActionType.SAMPLE_CREATION: 'SAMPLE',
        ActionType.MEASUREMENT: 'RAW_DATASET',
        ActionType.SIMULATION: 'RAW_DATASET'
    }
    for action_type_id, export_type in scicat_export_types.items():
        db.session.execute(db.text("""
            UPDATE action_types
            SET scicat_export_type = :export_type
            WHERE id = :id
        """), {
            "id": action_type_id,
            "export_type": export_type
        })
    return True
