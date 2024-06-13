# coding: utf-8
"""
Add the scicat_export_type column to the action_types table.
"""

import flask_sqlalchemy

from .utils import table_has_column
from ..actions import ActionType


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('action_types', 'scicat_export_type'):
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
