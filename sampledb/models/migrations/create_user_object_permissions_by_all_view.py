# coding: utf-8
"""
Create the view user_object_permissions_by_all to speed up object requests
with minimum permissions.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    table_exists = db.session.execute(db.text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'public_objects'
    """)).fetchall()
    if not table_exists:
        # the view as defined below depends on the removed public_objects table
        # see migration 97: replace_user_object_permissions_by_all_view.py
        return False

    # Perform migration
    db.session.execute(db.text("""
    CREATE OR REPLACE VIEW user_object_permissions_by_all
    AS
        SELECT
        NULL AS user_id,
        object_id AS object_id,
        1 AS permissions_int
        FROM public_objects
    UNION
        SELECT
        association.user_id AS user_id,
        objects.object_id AS object_id,
        3 AS permissions_int
        FROM association AS association
        JOIN actions AS actions ON association.instrument_id = actions.instrument_id
        JOIN objects_current AS objects ON objects.action_id = actions.id
    UNION
        SELECT
        user_object_permissions.user_id AS user_id,
        user_object_permissions.object_id AS object_id,
        ('{"READ": 1, "WRITE": 2, "GRANT": 3}'::jsonb ->> user_object_permissions.permissions::text)::int AS permissions_int
        FROM user_object_permissions
    UNION
        SELECT
        user_group_memberships.user_id AS user_id,
        group_object_permissions.object_id AS object_id,
        ('{"READ": 1, "WRITE": 2, "GRANT": 3}'::jsonb ->> group_object_permissions.permissions::text)::int AS permissions_int
        FROM user_group_memberships AS user_group_memberships
        JOIN group_object_permissions AS group_object_permissions ON user_group_memberships.group_id = group_object_permissions.group_id
    UNION
        SELECT
        user_project_permissions.user_id AS user_id,
        project_object_permissions.object_id AS object_id,
        LEAST(
            ('{"READ": 1, "WRITE": 2, "GRANT": 3}'::jsonb ->> project_object_permissions.permissions::text)::int,
            ('{"READ": 1, "WRITE": 2, "GRANT": 3}'::jsonb ->> user_project_permissions.permissions::text)::int
        ) AS permissions_int
        FROM user_project_permissions AS user_project_permissions
        JOIN project_object_permissions AS project_object_permissions ON user_project_permissions.project_id = project_object_permissions.project_id
    UNION
        SELECT
        user_group_memberships.user_id AS user_id,
        project_object_permissions.object_id AS object_id,
        LEAST(
            ('{"READ": 1, "WRITE": 2, "GRANT": 3}'::jsonb ->> project_object_permissions.permissions::text)::int,
            ('{"READ": 1, "WRITE": 2, "GRANT": 3}'::jsonb ->> group_project_permissions.permissions::text)::int
        ) AS permissions_int
        FROM user_group_memberships AS user_group_memberships
        JOIN group_project_permissions ON group_project_permissions.group_id = user_group_memberships.group_id
        JOIN project_object_permissions AS project_object_permissions ON group_project_permissions.project_id = project_object_permissions.project_id
    """))
    return True
