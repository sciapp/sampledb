# coding: utf-8
"""
Replace string columns with JSON columns in locations table.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_info = db.session.execute(db.text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'locations'
    """)).fetchall()
    if ('name', 'json') in column_info:
        return False

    # Perform migration
    existing_data = [
        location_data
        for location_data in db.session.execute(db.text("""
            SELECT id, name, description
            FROM locations
        """)).fetchall()
    ]

    db.session.execute(db.text("""
        ALTER TABLE locations
        DROP COLUMN name;
    """))
    db.session.execute(db.text("""
        ALTER TABLE locations
        DROP COLUMN description;
    """))
    db.session.execute(db.text("""
        ALTER TABLE locations
        ADD name JSON NOT NULL DEFAULT '{}'::json;
    """))
    db.session.execute(db.text("""
        ALTER TABLE locations
        ADD description JSON NOT NULL DEFAULT '{}'::json;
    """))
    for id, name, description in existing_data:
        location_data = {
            'id': id,
            'name': name,
            'description': description
        }
        db.session.execute(db.text("""
            UPDATE locations
            SET name = json_build_object('en', :name), description = json_build_object('en', :description)
            WHERE id = :id;
        """), params=location_data)
    return True
