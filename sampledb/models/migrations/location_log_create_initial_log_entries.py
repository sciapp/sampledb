# coding: utf-8
"""
Create location log entries for object location assignments created before the location log was implemented.
"""
import json
import typing

import flask_sqlalchemy

from ..location_log import LocationLogEntryType


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    location_log_entries_exist = db.session.execute(db.text("""
        SELECT id
        FROM location_log_entries
    """)).fetchone() is not None
    if location_log_entries_exist:
        return False

    object_location_assignments = db.session.execute(db.text("""
        SELECT id, location_id, user_id, object_id, utc_datetime
        FROM object_location_assignments
        ORDER BY utc_datetime ASC
    """)).fetchall()

    if not object_location_assignments:
        return False

    location_id_by_object_id: typing.Dict[int, int] = {}
    log_entries = []
    for object_location_assignment in object_location_assignments:
        object_location_assignment_id, location_id, user_id, object_id, utc_datetime = object_location_assignment
        previous_location_for_object = location_id_by_object_id.get(object_id)
        location_id_by_object_id[object_id] = location_id
        if location_id is not None and previous_location_for_object == location_id:
            log_entries.append({
                'type': LocationLogEntryType.CHANGE_OBJECT.name,
                'location_id': location_id,
                'utc_datetime': utc_datetime,
                'user_id': user_id,
                'data': json.dumps({
                    'object_location_assignment_id': object_location_assignment_id
                })
            })
        else:
            if previous_location_for_object is not None:
                log_entries.append({
                    'type': LocationLogEntryType.REMOVE_OBJECT.name,
                    'location_id': previous_location_for_object,
                    'utc_datetime': utc_datetime,
                    'user_id': user_id,
                    'data': json.dumps({
                        'object_location_assignment_id': object_location_assignment_id
                    })
                })
            if location_id is not None:
                log_entries.append({
                    'type': LocationLogEntryType.ADD_OBJECT.name,
                    'location_id': location_id,
                    'utc_datetime': utc_datetime,
                    'user_id': user_id,
                    'data': json.dumps({
                        'object_location_assignment_id': object_location_assignment_id
                    })
                })
    for log_entry in log_entries:
        db.session.execute(db.text("""
            INSERT INTO location_log_entries
            (type, location_id, utc_datetime, user_id, data)
            VALUES
            (CAST(:type AS locationlogentrytype), :location_id, :utc_datetime, :user_id, CAST(:data AS JSONB))
        """), params=log_entry)
    return True
