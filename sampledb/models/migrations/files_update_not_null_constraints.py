# coding: utf-8
"""
Replace NOT NULL constraints per column by NOT NULL constraints conditioned by federation reference in comments.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    constraints = db.session.execute(db.text("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'files_not_null_check'
    """)).fetchall()

    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE files
                ADD CONSTRAINT files_not_null_check
                    CHECK (
                        (
                            fed_id IS NOT NULL AND
                            component_id IS NOT NULL
                        ) OR (
                            user_id IS NOT NULL AND
                            utc_datetime IS NOT NULL
                        )
                    ),
                ALTER COLUMN user_id DROP NOT NULL,
                ALTER COLUMN utc_datetime DROP NOT NULL
        """))
    return True
