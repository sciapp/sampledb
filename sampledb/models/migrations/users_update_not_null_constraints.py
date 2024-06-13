# coding: utf-8
"""
Replace NOT NULL constraints per column by NOT NULL constraints conditioned by federation reference in objects_current.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    constraints = db.session.execute(db.text("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'users_not_null_check'
    """)).fetchall()

    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
            ADD CONSTRAINT users_not_null_check
                CHECK (
                    (
                        type = 'FEDERATION_USER' AND
                        NOT is_admin AND
                        fed_id IS NOT NULL AND
                        component_id IS NOT NULL
                    ) OR (
                        name IS NOT NULL AND
                        email IS NOT NULL
                    )
                ),
            ALTER COLUMN name DROP NOT NULL,
            ALTER COLUMN email DROP NOT NULL
    """))
    return True
