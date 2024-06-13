# coding: utf-8
"""
Add eln_import_id and eln_object_id columns to users table and update NOT NULL constraint.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
    """)).fetchall()
    if ('eln_import_id',) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE users
        ADD eln_import_id INTEGER,
        ADD eln_object_id VARCHAR,
        ADD CONSTRAINT fk_users_eln_import_id FOREIGN KEY (eln_import_id) REFERENCES eln_imports(id),
        ADD CONSTRAINT users_eln_import_id_eln_object_id_key UNIQUE(eln_import_id, eln_object_id)
    """))
    db.session.execute(db.text("""
        ALTER TABLE users
        DROP CONSTRAINT users_not_null_check
    """))
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
                    type = 'ELN_IMPORT_USER' AND
                    NOT is_admin AND
                    eln_import_id IS NOT NULL AND
                    eln_object_id IS NOT NULL
                ) OR (
                    name IS NOT NULL AND
                    email IS NOT NULL
                )
            )
    """))
    return True
