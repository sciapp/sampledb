# coding: utf-8
"""
Replace NOT NULL constraints per column by NOT NULL constraints conditioned by federation reference in comments.
"""

import os

MIGRATION_INDEX = 89
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    constraints = db.session.execute("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'comments_not_null_check'
    """).fetchall()

    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute("""
            ALTER TABLE comments
                ADD CONSTRAINT comments_not_null_check
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
        """)
    return True
