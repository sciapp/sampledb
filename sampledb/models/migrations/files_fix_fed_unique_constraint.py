# coding: utf-8
"""
Fix federation-related unique constraint for files table.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE files
            DROP CONSTRAINT IF EXISTS files_fed_id_component_id_key
    """))
    db.session.execute(db.text("""
        ALTER TABLE files
            ADD CONSTRAINT files_fed_id_component_id_key UNIQUE(fed_id, object_id, component_id)
    """))
    return True
