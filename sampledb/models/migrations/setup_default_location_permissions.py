# coding: utf-8
"""
Set WRITE permissions for all users for all existing locations if there are no
location permissions yet.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    existing_permissions = db.session.execute(db.text("""
        SELECT 1 FROM all_user_location_permissions
        UNION
        SELECT 1 FROM user_location_permissions
        UNION
        SELECT 1 FROM group_location_permissions
        UNION
        SELECT 1 FROM project_location_permissions
    """)).fetchall()
    if existing_permissions:
        return False

    # Perform migration
    existing_locations = db.session.execute(db.text("""
        SELECT id
        FROM locations
    """)).fetchall()
    for existing_location in existing_locations:
        db.session.execute(db.text("""
           INSERT INTO all_user_location_permissions
           (location_id, permissions)
           VALUES
           (:location_id, 'WRITE')
       """), {'location_id': existing_location[0]})
    return True
