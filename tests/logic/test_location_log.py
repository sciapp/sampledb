import pytest

import sampledb


def test_get_log_entries_for_location():
    user = sampledb.logic.users.create_user(
        name='Test User',
        email='example@example.org',
        type=sampledb.logic.users.UserType.PERSON
    )
    location = sampledb.logic.locations.create_location(
        {'en': 'Test Location'},
        {},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    with pytest.raises(sampledb.logic.errors.LocationDoesNotExistError):
        sampledb.logic.location_log.get_log_entries_for_location(location_id=location.id + 1, user_id=None)
    assert [
        (log_entry, log_entry.update({'utc_datetime': None}))[0]
        for log_entry in sampledb.logic.location_log.get_log_entries_for_location(location_id=location.id, user_id=None)
    ] == [
        {
            'type': sampledb.logic.location_log.LocationLogEntryType.CREATE_LOCATION,
            'utc_datetime': None,
            'user_id': user.id,
            'user': user,
            'location_id': location.id,
            'data': {}
        }
    ]
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Test Schema',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': {'en': 'Test'}
            }
        },
        user_id=user.id
    )
    sampledb.logic.locations.assign_location_to_object(
        object_id=object.id,
        location_id=location.id,
        responsible_user_id=None,
        user_id=user.id,
        description=None
    )
    object_location_assignment = sampledb.logic.locations.get_current_object_location_assignment(object_id=object.id)
    assert [
        (log_entry, log_entry.update({'utc_datetime': None}))[0]
        for log_entry in sampledb.logic.location_log.get_log_entries_for_location(location_id=location.id, user_id=None)
    ] == [
        {
            'type': sampledb.logic.location_log.LocationLogEntryType.ADD_OBJECT,
            'utc_datetime': None,
            'user_id': user.id,
            'user': user,
            'location_id': location.id,
            'data': {'object_location_assignment_id': object_location_assignment.id},
            'object_id': object.id,
            'object': None,
            'object_location_assignment': object_location_assignment
        },
        {
            'type': sampledb.logic.location_log.LocationLogEntryType.CREATE_LOCATION,
            'utc_datetime': None,
            'user_id': user.id,
            'user': user,
            'location_id': location.id,
            'data': {}
        }
    ]
    assert [
        (log_entry, log_entry.update({'utc_datetime': None}))[0]
        for log_entry in sampledb.logic.location_log.get_log_entries_for_location(location_id=location.id, user_id=user.id)
    ] == [
        {
            'type': sampledb.logic.location_log.LocationLogEntryType.ADD_OBJECT,
            'utc_datetime': None,
            'user_id': user.id,
            'user': user,
            'location_id': location.id,
            'data': {'object_location_assignment_id': object_location_assignment.id},
            'object_id': object.id,
            'object': object,
            'object_location_assignment': object_location_assignment
        },
        {
            'type': sampledb.logic.location_log.LocationLogEntryType.CREATE_LOCATION,
            'utc_datetime': None,
            'user_id': user.id,
            'user': user,
            'location_id': location.id,
            'data': {}
        }
    ]
    location2 = sampledb.logic.locations.create_location(
        {'en': 'Test Location'},
        {},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    sampledb.logic.locations.assign_location_to_object(
        object_id=object.id,
        location_id=location2.id,
        responsible_user_id=None,
        user_id=user.id,
        description=None
    )
    object_location_assignment2 = sampledb.logic.locations.get_current_object_location_assignment(object_id=object.id)
    assert [
        (log_entry, log_entry.update({'utc_datetime': None}))[0]
        for log_entry in sampledb.logic.location_log.get_log_entries_for_location(location_id=location.id, user_id=user.id)
    ] == [
        {
            'type': sampledb.logic.location_log.LocationLogEntryType.REMOVE_OBJECT,
            'utc_datetime': None,
            'user_id': user.id,
            'user': user,
            'location_id': location.id,
            'data': {'object_location_assignment_id': object_location_assignment2.id},
            'object_id': object.id,
            'object': object,
            'object_location_assignment': object_location_assignment2,
            'new_location_id': location2.id,
            'new_location': location2
        },
        {
            'type': sampledb.logic.location_log.LocationLogEntryType.ADD_OBJECT,
            'utc_datetime': None,
            'user_id': user.id,
            'user': user,
            'location_id': location.id,
            'data': {'object_location_assignment_id': object_location_assignment.id},
            'object_id': object.id,
            'object': object,
            'object_location_assignment': object_location_assignment
        },
        {
            'type': sampledb.logic.location_log.LocationLogEntryType.CREATE_LOCATION,
            'utc_datetime': None,
            'user_id': user.id,
            'user': user,
            'location_id': location.id,
            'data': {}
        }
    ]