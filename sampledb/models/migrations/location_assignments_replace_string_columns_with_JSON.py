# coding: utf-8
"""
Replace string description column with JSON column in object_location_assignments table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 57
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_info = db.session.execute(db.text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'object_location_assignments'
    """)).fetchall()
    if ('description', 'json') in column_info:
        return False

    # Perform migration
    existing_data = [
        location_assignment_data
        for location_assignment_data in db.session.execute(db.text("""
            SELECT id, description
            FROM object_location_assignments
        """)).fetchall()
    ]

    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        DROP COLUMN description;
    """))
    db.session.execute(db.text("""
        ALTER TABLE object_location_assignments
        ADD description JSON NOT NULL DEFAULT '{}'::json;
    """))
    for id, description in existing_data:
        location_assignment_data = {
            'id': id,
            'description': description
        }
        db.session.execute(db.text("""
            UPDATE object_location_assignments
            SET description = json_build_object('en', :description)
            WHERE id = :id;
        """), params=location_assignment_data)
    return True
