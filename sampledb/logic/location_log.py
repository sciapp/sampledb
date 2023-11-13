import datetime
import typing

from .. import db
from .. import models
from ..models import LocationLogEntryType
from . import errors, users, locations, object_permissions, objects


def get_log_entries_for_location(
        location_id: int,
        user_id: typing.Optional[int]
) -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Return a list of log entries for a given location.

    Log entries are returned as dicts, with log entries of some types
    augmented with auxiliary information, such as a referenced object location
    assignment or object. The given user ID will be used to ensure that only
    information which the user may access will be returned.

    :param location_id: the ID of an existing location
    :param user_id: the ID of an existing user, or None
    :return: the location log entries
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """

    log_entries = []
    users_by_id: typing.Dict[typing.Optional[int], typing.Optional[users.User]] = {None: None}
    locations_by_id = {}
    objects_by_id = {}
    for log_entry in models.LocationLogEntry.query.filter_by(
        location_id=location_id
    ).order_by(
        db.desc(models.LocationLogEntry.utc_datetime)
    ).all():
        log_entries.append({
            'type': log_entry.type,
            'utc_datetime': log_entry.utc_datetime,
            'user_id': log_entry.user_id,
            'location_id': log_entry.location_id,
            'data': log_entry.data
        })
        if log_entry.user_id not in users_by_id and log_entry.user_id is not None:
            try:
                users_by_id[log_entry.user_id] = users.get_user(log_entry.user_id)
            except errors.UserDoesNotExistError:
                users_by_id[log_entry.user_id] = None
        log_entries[-1]['user'] = users_by_id[log_entry.user_id]
        object_location_assignment_id = log_entry.data.get('object_location_assignment_id')
        if object_location_assignment_id:
            try:
                object_location_assignment = locations.get_object_location_assignment(object_location_assignment_id)
            except errors.ObjectLocationAssignmentDoesNotExistError:
                object_location_assignment = None
            log_entries[-1]['object_location_assignment'] = object_location_assignment
            if object_location_assignment is not None:
                object_id = object_location_assignment.object_id
                log_entries[-1]['object_id'] = object_id
                if object_id not in objects_by_id:
                    try:
                        if models.Permissions.READ in object_permissions.get_user_object_permissions(object_id, user_id):
                            object = objects.get_object(object_id)
                        else:
                            object = None
                    except errors.ObjectDoesNotExistError:
                        object = None
                    objects_by_id[object_id] = object
                log_entries[-1]['object'] = objects_by_id[object_id]
                if object_location_assignment.location_id != location_id:
                    new_location_id = object_location_assignment.location_id
                    log_entries[-1]['new_location_id'] = new_location_id
                    if new_location_id not in locations_by_id:
                        new_location = None
                        if new_location_id is not None:
                            try:
                                new_location = locations.get_location(new_location_id)
                            except errors.LocationDoesNotExistError:
                                pass
                        locations_by_id[new_location_id] = new_location
                    log_entries[-1]['new_location'] = locations_by_id[new_location_id]
    if not log_entries:
        # ensure the location exists
        locations.check_location_exists(location_id)
    return log_entries


def _store_new_log_entry(
        type: LocationLogEntryType,
        location_id: int,
        user_id: typing.Optional[int],
        data: typing.Dict[str, typing.Any]
) -> None:
    user_log_entry = models.LocationLogEntry(
        type=type,
        location_id=location_id,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(user_log_entry)
    db.session.commit()


def create_location(user_id: typing.Optional[int], location_id: int) -> None:
    _store_new_log_entry(
        type=LocationLogEntryType.CREATE_LOCATION,
        location_id=location_id,
        user_id=user_id,
        data={
        }
    )


def update_location(user_id: typing.Optional[int], location_id: int) -> None:
    _store_new_log_entry(
        type=LocationLogEntryType.UPDATE_LOCATION,
        location_id=location_id,
        user_id=user_id,
        data={
        }
    )


def add_object(user_id: typing.Optional[int], location_id: int, object_location_assignment_id: int) -> None:
    _store_new_log_entry(
        type=LocationLogEntryType.ADD_OBJECT,
        location_id=location_id,
        user_id=user_id,
        data={
            'object_location_assignment_id': object_location_assignment_id
        }
    )


def change_object(user_id: typing.Optional[int], location_id: int, object_location_assignment_id: int) -> None:
    _store_new_log_entry(
        type=LocationLogEntryType.CHANGE_OBJECT,
        location_id=location_id,
        user_id=user_id,
        data={
            'object_location_assignment_id': object_location_assignment_id
        }
    )


def remove_object(user_id: typing.Optional[int], location_id: int, object_location_assignment_id: int) -> None:
    _store_new_log_entry(
        type=LocationLogEntryType.REMOVE_OBJECT,
        location_id=location_id,
        user_id=user_id,
        data={
            'object_location_assignment_id': object_location_assignment_id
        }
    )
