# coding: utf-8
"""
Replace the default_public_permissions table with the all_user_default_permissions table.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    table_exists = db.session.execute(db.text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'default_public_permissions'
    """)).fetchall()
    if not table_exists:
        return False

    # Perform migration
    default_public_permissions = db.session.execute(db.text("""
        SELECT creator_id
        FROM default_public_permissions
        WHERE is_public = true
    """)).fetchall()
    all_user_default_permissions = db.session.execute(db.text("""
        SELECT creator_id, permissions
        FROM all_user_default_permissions
    """)).fetchall()
    all_user_object_permissions = {
        creator_id: permissions
        for creator_id, permissions in all_user_default_permissions
    }
    for creator_id, in default_public_permissions:
        if creator_id not in all_user_object_permissions:
            db.session.execute(db.text("""
                INSERT INTO all_user_default_permissions
                (creator_id, permissions)
                VALUES (:creator_id, 'READ')
            """), {'creator_id': creator_id})
    db.session.execute(db.text("""
        DROP TABLE default_public_permissions
    """))
    return True
