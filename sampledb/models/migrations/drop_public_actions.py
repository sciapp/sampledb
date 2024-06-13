# coding: utf-8
"""
Replace the public_actions table with the all_user_action_permissions table.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    table_exists = db.session.execute(db.text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'public_actions'
    """)).fetchall()
    if not table_exists:
        return False

    # Perform migration
    public_actions = db.session.execute(db.text("""
        SELECT action_id
        FROM public_actions
    """)).fetchall()
    all_user_action_permissions_result = db.session.execute(db.text("""
        SELECT action_id, permissions
        FROM all_user_action_permissions
    """)).fetchall()
    all_user_action_permissions = {
        action_id: permissions
        for action_id, permissions in all_user_action_permissions_result
    }
    for action_id, in public_actions:
        if action_id not in all_user_action_permissions:
            db.session.execute(db.text("""
                INSERT INTO all_user_action_permissions
                (action_id, permissions)
                VALUES (:action_id, 'READ')
            """), {'action_id': action_id})
    db.session.execute(db.text("""
        DROP TABLE public_actions
    """))
    return True
