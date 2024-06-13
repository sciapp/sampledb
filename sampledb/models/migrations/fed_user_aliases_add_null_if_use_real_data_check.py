# coding: utf-8
"""
Add null if use_real_* is set check to fed_user_aliases.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    constraints = db.session.execute(db.text("""
         SELECT conname
         FROM pg_catalog.pg_constraint
         WHERE conname = 'fed_user_alias_null_if_use_real_data'
    """)).fetchall()

    if len(constraints) > 0:
        return False

    # Perform migration
    db.session.execute(db.text("""
            ALTER TABLE fed_user_aliases
                ADD CONSTRAINT fed_user_alias_null_if_use_real_data
                    CHECK ((name IS NULL OR use_real_name IS FALSE) AND
                        (use_real_email IS FALSE OR email IS NULL) AND
                        (orcid IS NULL OR use_real_orcid IS FALSE) AND
                        (affiliation IS NULL OR use_real_affiliation IS FALSE) AND
                        (role IS NULL OR use_real_role IS FALSE)
                    )
        """))
    return True
