# coding: utf-8
"""
Replace NOT NULL constraints per column by NOT NULL constraints conditioned by federation reference in objects_current.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    constraints = db.session.execute(db.text("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'objects_current_not_null_check'
    """)).fetchall()

    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_current
            ADD CONSTRAINT objects_current_not_null_check
                CHECK (
                    (
                        fed_object_id IS NOT NULL AND
                        fed_version_id IS NOT NULL AND
                        component_id IS NOT NULL
                    ) OR (
                        action_id IS NOT NULL AND
                        data IS NOT NULL AND
                        schema IS NOT NULL AND
                        user_id IS NOT NULL AND
                        utc_datetime IS NOT NULL
                    )
                ),
            ALTER COLUMN action_id DROP NOT NULL,
            ALTER COLUMN data DROP NOT NULL,
            ALTER COLUMN schema DROP NOT NULL,
            ALTER COLUMN user_id DROP NOT NULL,
            ALTER COLUMN utc_datetime DROP NOT NULL
    """))
    return True
