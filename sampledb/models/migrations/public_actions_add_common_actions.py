# coding: utf-8
"""
Add entries to the public_actions table for all actions without a user_id.

Previously, these actions were implicitly public.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Perform migration
    common_actions_result = db.session.execute(db.text("""
        SELECT id
        FROM actions
        WHERE user_id IS NULL
    """))
    common_actions = {row[0] for row in common_actions_result}

    table_exists = db.session.execute(db.text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'public_actions'
    """)).fetchall()
    if table_exists:
        public_actions_result = db.session.execute(db.text("""
            SELECT action_id
            FROM public_actions
        """))
        public_actions = {row[0] for row in public_actions_result}
        for action_id in common_actions - public_actions:
            db.session.execute(db.text("""
                INSERT INTO public_actions
                (action_id)
                VALUES
                (:action_id)
            """), {'action_id': action_id})
    else:
        all_user_action_permissions_result = db.session.execute(db.text("""
            SELECT action_id, permissions
            FROM all_user_action_permissions
        """)).fetchall()
        all_user_action_permissions = {
            action_id: permissions
            for action_id, permissions in all_user_action_permissions_result
        }
        for action_id in common_actions:
            if action_id not in all_user_action_permissions:
                db.session.execute(db.text("""
                    INSERT INTO public_actions
                    (action_id, permissions)
                    VALUES (:action_id, 'READ')
                """), {'action_id': action_id})
    return True
