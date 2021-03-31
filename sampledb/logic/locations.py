# coding: utf-8
"""
Logic module for locations and object location assignments.

Locations are fully user-defined using a name and a description. Users with
WRITE permissions for an object can assign it to a location with an optional
description for details on where the object is stored.
"""

import collections
import datetime
import typing

from .. import db
from . import user_log, object_log, objects, users, errors, languages
from .notifications import create_notification_for_being_assigned_as_responsible_user
from ..models import locations


class Location(collections.namedtuple('Location', ['id', 'name', 'description', 'parent_location_id'])):
    """
    This class provides an immutable wrapper around models.locations.Location.
    """

    def __new__(cls, id: int, name: dict, description: dict, parent_location_id: typing.Optional[int] = None):
        self = super(Location, cls).__new__(cls, id, name, description, parent_location_id)
        return self

    @classmethod
    def from_database(cls, location: locations.Location) -> 'Location':
        return Location(
            id=location.id,
            name=location.name,
            description=location.description,
            parent_location_id=location.parent_location_id
        )


class ObjectLocationAssignment(collections.namedtuple('ObjectLocationAssignment', ['id', 'object_id', 'location_id', 'user_id', 'description', 'utc_datetime', 'responsible_user_id', 'confirmed'])):
    """
    This class provides an immutable wrapper around models.locations.ObjectLocationAssignment.
    """

    def __new__(cls, id: int, object_id: int, location_id: int, user_id: int, description: dict, utc_datetime: datetime.datetime, responsible_user_id: int, confirmed: bool):
        self = super(ObjectLocationAssignment, cls).__new__(cls, id, object_id, location_id, user_id, description, utc_datetime, responsible_user_id, confirmed)
        return self

    @classmethod
    def from_database(cls, object_location_assignment: locations.ObjectLocationAssignment) -> 'ObjectLocationAssignment':
        return ObjectLocationAssignment(
            id=object_location_assignment.id,
            object_id=object_location_assignment.object_id,
            location_id=object_location_assignment.location_id,
            responsible_user_id=object_location_assignment.responsible_user_id,
            user_id=object_location_assignment.user_id,
            description=object_location_assignment.description,
            utc_datetime=object_location_assignment.utc_datetime,
            confirmed=object_location_assignment.confirmed
        )


def create_location(name: typing.Union[str, dict], description: typing.Union[str, dict], parent_location_id: typing.Optional[int], user_id: int) -> Location:
    """
    Create a new location.

    :param name: the names for the new location in a dict. Keys are the language codes and values are the names.
    :param description: the descriptions for the new location.
        Keys are the language code and values are the descriptions.
    :param parent_location_id: the optional parent location ID for the new location
    :param user_id: the ID of an existing user
    :return: the created location
    :raise errors.LocationDoesNotExistError: when no location with the given
        parent location ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    if isinstance(name, str):
        name = {
            'en': name
        }
    if isinstance(description, str):
        description = {
            'en': description
        }

    allowed_language_codes = {
        language.lang_code
        for language in languages.get_languages(only_enabled_for_input=True)
    }

    for language_code, name_text in list(name.items()):
        if language_code not in allowed_language_codes:
            raise errors.LanguageDoesNotExistError()
        if not name_text:
            del name[language_code]

    for language_code, description_text in list(description.items()):
        if language_code not in allowed_language_codes:
            raise errors.LanguageDoesNotExistError()
        if not description_text:
            del description[language_code]

    if 'en' not in name:
        raise errors.MissingEnglishTranslationError()

    # ensure the user exists
    users.get_user(user_id)
    if parent_location_id is not None:
        # ensure parent location exists
        get_location(parent_location_id)
    location = locations.Location(
        name=name,
        description=description,
        parent_location_id=parent_location_id
    )
    db.session.add(location)
    db.session.commit()
    user_log.create_location(user_id, location.id)
    return Location.from_database(location)


def update_location(location_id: int, name: dict, description: dict, parent_location_id: typing.Optional[int], user_id: int) -> None:
    """
    Update a location's information.

    :param location_id: the ID of the location to update
    :param name: the new names for the location in a dict. Keys are the language codes and the values the new names
    :param description: the descriptions for the location.
        Keys are the language code and the values the new descriptions.
    :param parent_location_id: the optional parent location id for the location
    :param user_id: the ID of an existing user
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID or parent location ID exists
    :raise errors.CyclicLocationError: when location ID is an ancestor of
        parent location ID
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.MissingEnglishTranslationError: if no english name is given
    :raise errors.LanguageDoesNotExistError: if an unknown language code is
        used
    """

    allowed_language_codes = {
        language.lang_code
        for language in languages.get_languages(only_enabled_for_input=True)
    }

    for language_code, name_text in list(name.items()):
        if language_code not in allowed_language_codes:
            raise errors.LanguageDoesNotExistError()
        if not name_text:
            del name[language_code]

    for language_code, description_text in list(description.items()):
        if language_code not in allowed_language_codes:
            raise errors.LanguageDoesNotExistError()
        if not description_text:
            del description[language_code]

    if 'en' not in name:
        raise errors.MissingEnglishTranslationError()

    # ensure the user exists
    users.get_user(user_id)
    location = locations.Location.query.filter_by(id=location_id).first()
    if location is None:
        raise errors.LocationDoesNotExistError()
    if parent_location_id is not None:
        if location_id == parent_location_id or location_id in _get_location_ancestors(parent_location_id):
            raise errors.CyclicLocationError()
    location.name = name
    location.description = description
    location.parent_location_id = parent_location_id
    db.session.add(location)
    db.session.commit()
    user_log.update_location(user_id, location.id)


def get_location(location_id: int) -> Location:
    """
    Get a location.

    :param location_id: the ID of an existing location
    :raise errors.LocationDoesNotExistError: when no location with the given
        parent location ID exists
    :return: the location with the given location ID
    """
    location = locations.Location.query.filter_by(id=location_id).first()
    if location is None:
        raise errors.LocationDoesNotExistError()
    return Location.from_database(location)


def get_locations() -> typing.List[Location]:
    """
    Get the list of all locations.

    :return: the list of all locations
    """
    return [
        Location.from_database(location)
        for location in locations.Location.query.all()
    ]


def get_locations_tree() -> typing.Tuple[typing.Dict[int, Location], typing.Any]:
    """
    Get the list of locations as a tree.

    :return: the list of all locations and the locations tree
    """
    locations = get_locations()
    locations_map = {
        location.id: location
        for location in locations
    }
    locations_tree = {}
    locations_tree_helper = {None: locations_tree}
    unvisited_locations = locations
    while unvisited_locations:
        locations = unvisited_locations
        unvisited_locations = []
        for location in locations:
            if location.parent_location_id in locations_tree_helper:
                locations_subtree = locations_tree_helper[location.parent_location_id]
                locations_subtree[location.id] = {}
                locations_tree_helper[location.id] = locations_subtree[location.id]
            else:
                unvisited_locations.append(location)
    return locations_map, locations_tree


def _get_location_ancestors(location_id: int) -> typing.List[int]:
    """
    Get the list of all ancestor location IDs.

    :param location_id: the ID of an existing location
    :return: the list of all ancestor location IDs
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    ancestor_location_ids = []
    while location_id is not None:
        ancestor_location_ids.append(location_id)
        location_id = get_location(location_id).parent_location_id
    return ancestor_location_ids[1:]


def assign_location_to_object(object_id: int, location_id: typing.Optional[int], responsible_user_id: typing.Optional[int], user_id: int, description: typing.Union[str, dict]) -> None:
    """
    Assign a location to an object.

    :param object_id: the ID of an existing object
    :param location_id: the ID of an existing location
    :param responsible_user_id: the ID of an existing user
    :param user_id: the ID of an existing user
    :param description: a description of where the object was stored in a dict.
        The keys are the lang codes and the values are the descriptions.
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        or responsible user ID exists
    """
    if isinstance(description, str):
        description = {
            'en': description
        }
    # ensure the object exists
    objects.get_object(object_id)
    if location_id is not None:
        # ensure the location exists
        get_location(location_id)
    # ensure the user exists
    users.get_user(user_id)
    object_location_assignment = locations.ObjectLocationAssignment(
        object_id=object_id,
        location_id=location_id,
        responsible_user_id=responsible_user_id,
        user_id=user_id,
        description=description,
        utc_datetime=datetime.datetime.utcnow(),
        confirmed=(user_id == responsible_user_id)
    )
    db.session.add(object_location_assignment)
    db.session.commit()
    if responsible_user_id is not None:
        users.get_user(responsible_user_id)
        if user_id != responsible_user_id:
            create_notification_for_being_assigned_as_responsible_user(object_location_assignment.id)
    object_log.assign_location(user_id, object_id, object_location_assignment.id)
    user_log.assign_location(user_id, object_location_assignment.id)


def get_object_location_assignments(object_id: int) -> typing.List[ObjectLocationAssignment]:
    """
    Get a list of all object location assignments for an object.

    :param object_id: the ID of an existing object
    :return: the list of object location assignments
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    # ensure the object exists
    objects.get_object(object_id)
    object_location_assignments = locations.ObjectLocationAssignment.query.filter_by(object_id=object_id).order_by(locations.ObjectLocationAssignment.utc_datetime).all()
    return [
        ObjectLocationAssignment.from_database(object_location_assignment)
        for object_location_assignment in object_location_assignments
    ]


def get_current_object_location_assignment(object_id: int) -> typing.Optional[ObjectLocationAssignment]:
    """
    Get the current location assignment for an object.

    :param object_id: the ID of an existing object
    :return: the object location assignment
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    # ensure the object exists
    objects.get_object(object_id)
    object_location_assignment = locations.ObjectLocationAssignment.query.filter_by(object_id=object_id).order_by(locations.ObjectLocationAssignment.utc_datetime.desc()).first()
    if object_location_assignment is not None:
        object_location_assignment = ObjectLocationAssignment.from_database(object_location_assignment)
    return object_location_assignment


def get_object_location_assignment(object_location_assignment_id: int) -> ObjectLocationAssignment:
    """
    Get an object location assignment with a given ID.

    :param object_location_assignment_id: the ID of an existing object location
        assignment
    :return: the object location assignment
    :raise errors.ObjectLocationAssignmentDoesNotExistError: when no object
        location assignment with the given object location assignment ID exists
    """
    object_location_assignment = locations.ObjectLocationAssignment.query.filter_by(id=object_location_assignment_id).first()
    if object_location_assignment is None:
        raise errors.ObjectLocationAssignmentDoesNotExistError()
    return object_location_assignment


def get_object_ids_at_location(location_id: int) -> typing.Set[int]:
    """
    Get a list of all objects currently assigned to a location.

    :param location_id: the ID of an existing location
    :return: the list of object IDs assigned to the location
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    # ensure the location exists
    get_location(location_id)
    object_location_assignments = locations.ObjectLocationAssignment.query.filter_by(location_id=location_id).all()
    object_ids = set()
    for object_location_assignment in object_location_assignments:
        object_id = object_location_assignment.object_id
        if get_current_object_location_assignment(object_id).location_id == location_id:
            object_ids.add(object_id)
    return object_ids


def confirm_object_responsibility(object_location_assignment_id: int) -> None:
    """
    Confirm an object location assignment.

    :param object_location_assignment_id: the ID of an existing object location
        assignment
    :raise errors.ObjectLocationAssignmentDoesNotExistError: when no object
        location assignment with the given object location assignment ID exists
    """
    object_location_assignment = locations.ObjectLocationAssignment.query.filter_by(id=object_location_assignment_id).first()
    object_location_assignment.confirmed = True
    db.session.add(object_location_assignment)
    db.session.commit()
