# coding: utf-8
"""
Add entries to the public_actions table for all actions without a user_id.

Previously, these actions were implicitly public.
"""

import os

MIGRATION_INDEX = 47
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Perform migration
    common_actions = db.session.execute("""
        SELECT id
        FROM actions
        WHERE user_id IS NULL
    """)
    common_actions = {row[0] for row in common_actions}
    public_actions = db.session.execute("""
        SELECT action_id
        FROM public_actions
    """)
    public_actions = {row[0] for row in public_actions}
    for action_id in common_actions - public_actions:
        db.session.execute("""
            INSERT INTO public_actions
            (action_id)
            VALUES
            (:action_id)
        """, {'action_id': action_id})
    return True
