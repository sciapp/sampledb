# coding: utf-8
"""
Replace string columns with JSON columns in groups table.
"""

import os

MIGRATION_INDEX = 55
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    # Skip migration by condition
    column_names = db.session.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'groups'
    """).fetchall()
    if ('name', 'json') in column_names and ('description', 'json') in column_names:
        return False

        # Perform migration
    existing_data = [
        group_data
        for group_data in db.session.execute("""
               SELECT id, name, description
               FROM groups
           """).fetchall()
    ]

    db.session.execute("""
           ALTER TABLE groups
           DROP COLUMN name;
       """)
    db.session.execute("""
           ALTER TABLE groups
           DROP COLUMN description;
       """)
    db.session.execute("""
           ALTER TABLE groups
           ADD name JSON NOT NULL DEFAULT '{}'::json;
       """)
    db.session.execute("""
           ALTER TABLE groups
           ADD description JSON NOT NULL DEFAULT '{}'::json;
       """)
    for id, name, description in existing_data:
        group_data = {
            'id': id,
            'name': name,
            'description': description
        }
        db.session.execute("""
               UPDATE groups
               SET name = json_build_object('en', :name), description = json_build_object('en', :description)
               WHERE id = :id;
           """, params=group_data)
    return True
