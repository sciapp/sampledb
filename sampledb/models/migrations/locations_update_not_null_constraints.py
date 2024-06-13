# coding: utf-8
"""
Replace NOT NULL constraints on name by NOT NULL constraint conditioned by federation reference in locations.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    constraints = db.session.execute(db.text("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'locations_not_null_check'
    """)).fetchall()

    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE locations
            ADD CONSTRAINT locations_not_null_check
                CHECK (
                    (
                        fed_id IS NOT NULL AND
                        component_id IS NOT NULL
                    ) OR (
                        name is NOT NULL AND
                        description IS NOT NULL
                    )
                ),
            ALTER COLUMN name DROP NOT NULL,
            ALTER COLUMN description DROP NOT NULL
    """))
    return True
