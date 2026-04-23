"""
Init imported_from_component_id column of object_location_assignments table.
"""

import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    component_ids = db.session.execute(db.text("""
        SELECT imported_from_component_id
        FROM object_location_assignments
        WHERE component_id IS NOT NULL
    """)).fetchall()

    if len(component_ids) == 0 or set(component_ids) != {(None, )}:
        return False

    # Perform migration
    db.session.execute(db.text("""
        UPDATE object_location_assignments
        SET imported_from_component_id = component_id
    """))
    return True
