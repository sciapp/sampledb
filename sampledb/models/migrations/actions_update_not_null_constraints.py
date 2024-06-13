# coding: utf-8
"""
Replace NOT NULL constraints per column by NOT NULL constraints conditioned by federation reference in actions.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    constraints = db.session.execute(db.text("""
             SELECT conname
             FROM pg_catalog.pg_constraint
             WHERE conname = 'actions_not_null_check'
        """)).fetchall()
    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE actions
            ADD CONSTRAINT actions_not_null_check
                CHECK ((
                    fed_id IS NOT NULL AND
                    component_id IS NOT NULL
                ) OR (
                    type_id IS NOT NULL AND
                    schema IS NOT NULL
                )),
            ALTER COLUMN type_id DROP NOT NULL,
            ALTER COLUMN schema DROP NOT NULL
    """))
    return True
