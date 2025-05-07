"""
Update hash_data and hash_metadata columns for local objects in objects_current and objects_previous
"""
import flask_sqlalchemy

from ...logic.federation.conflicts import calculate_data_hash, calculate_metadata_hash


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migrations by condition
    hashes = db.session.execute(db.text("""
        SELECT hash_data
        FROM objects_current
        WHERE component_id IS NULL
    """)).fetchall()

    object_count = db.session.execute(db.text("""
        SELECT COUNT(*)
        FROM objects_current
        WHERE component_id IS NULL
    """)).scalar()

    if hashes != [(None, )] or object_count == 0:
        return False

    # Perform migration
    existing_current_objects = db.session.execute(db.text("""
        SELECT object_id, data, schema, user_id, utc_datetime
        FROM objects_current
        WHERE component_id IS NULL
    """)).fetchall()

    existing_previous_objects = db.session.execute(db.text("""
        SELECT object_id, data, schema, user_id, utc_datetime
        FROM objects_previous
        WHERE component_id IS NULL
    """)).fetchall()

    objects_current_query_params = []
    objects_previous_query_params = []
    for id, data, schema, user_id, utc_datetime in existing_current_objects:
        objects_current_query_params.append({
            'hash_data': calculate_data_hash(data, schema, id),
            'hash_metadata': calculate_metadata_hash(user_id, utc_datetime),
            'object_id': id
        })

    for id, data, schema, user_id, utc_datetime in existing_previous_objects:
        objects_previous_query_params.append({
            'hash_data': calculate_data_hash(data, schema, id),
            'hash_metadata': calculate_metadata_hash(user_id, utc_datetime),
            'object_id': id,
        })

    for params in objects_current_query_params:
        db.session.execute(db.text("""
            UPDATE objects_current
            SET hash_data = :hash_data, hash_metadata = :hash_metadata
            WHERE object_id = :object_id
        """), params)

    for params in objects_previous_query_params:
        db.session.execute(db.text("""
            UPDATE objects_previous
            SET hash_data = :hash_data, hash_metadata = :hash_metadata
            WHERE object_id = :object_id
        """), params)
    return True
