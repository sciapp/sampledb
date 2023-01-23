# coding: utf-8
"""
Create default location types.
"""
import json
import os

import flask_sqlalchemy

from ..locations import LocationType

MIGRATION_INDEX = 115
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    location_types_column_names = db.session.execute(db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'location_types'
        """)).fetchall()
    has_enable_instruments = ('enable_instruments',) in location_types_column_names

    existing_location_type_ids = [
        location_type[0]
        for location_type in db.session.execute(db.text("""
                    SELECT id
                    FROM location_types;
                """)).fetchall()
    ]

    # checks if translatable columns still exist in action_types
    default_location_types = [
        {
            'id': LocationType.LOCATION,
            'name': json.dumps({'en': 'Locations', 'de': 'Orte'}),
            'location_name_singular': json.dumps({'en': 'Location', 'de': 'Ort'}),
            'location_name_plural': json.dumps({'en': 'Locations', 'de': 'Orte'}),
            'admin_only': False,
            'enable_parent_location': True,
            'enable_sub_locations': True,
            'enable_object_assignments': True,
            'enable_responsible_users': False,
            'show_location_log': False,
            'enable_instruments': True
        }
    ]

    performed_migration = False
    for location_type in default_location_types:
        # Skip migration by condition
        if location_type['id'] in existing_location_type_ids:
            continue

        # Perform migration
        if has_enable_instruments:
            db.session.execute(db.text("""
                INSERT INTO location_types (id, name, location_name_singular, location_name_plural, admin_only, enable_parent_location, enable_sub_locations, enable_object_assignments, enable_responsible_users, show_location_log, enable_instruments)
                VALUES (:id, :name, :location_name_singular, :location_name_plural, :admin_only, :enable_parent_location, :enable_sub_locations, :enable_object_assignments, :enable_responsible_users, :show_location_log, :enable_instruments)
            """), params=location_type)
        else:
            db.session.execute(db.text("""
                INSERT INTO location_types (id, name, location_name_singular, location_name_plural, admin_only, enable_parent_location, enable_sub_locations, enable_object_assignments, enable_responsible_users, show_location_log)
                VALUES (:id, :name, :location_name_singular, :location_name_plural, :admin_only, :enable_parent_location, :enable_sub_locations, :enable_object_assignments, :enable_responsible_users, :show_location_log)
            """), params=location_type)
        performed_migration = True

    return performed_migration
