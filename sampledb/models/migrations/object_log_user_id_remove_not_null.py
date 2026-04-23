"""
Remove not null constraint from user_id in object_log_entries. Only allow null for type SOLVE_VERSION_CONFLICT
"""

import flask_sqlalchemy

from .utils import column_is_nullable


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if column_is_nullable("object_log_entries", "user_id"):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_log_entries
        ALTER COLUMN user_id DROP NOT NULL
    """))

    db.session.execute(db.text("""
        ALTER TABLE object_log_entries
        ADD CONSTRAINT object_log_user_id_nullable CHECK (
            (
                type != 'SOLVE_VERSION_CONFLICT' AND
                user_id IS NOT NULL
            ) OR (
                type = 'SOLVE_VERSION_CONFLICT' AND (
                    user_id IS NOT NULL OR (
                        user_id IS NULL AND
                        ((data->>'automerged')::boolean) = true
                    )
                )
            )
        )
    """))
    return True
