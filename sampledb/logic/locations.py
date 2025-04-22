# coding: utf-8
"""
Logic module for locations and object location assignments.

Locations are fully user-defined using a name and a description. Users with
WRITE permissions for an object can assign it to a location with an optional
description for details on where the object is stored.
"""

import dataclasses
import datetime
import typing

from .components import Component
from . import actions, topics
from .action_types import check_action_type_exists
from .. import db, models, logic
from . import user_log, object_log, location_log, objects, users, errors, languages, components
from .notifications import create_notification_for_being_assigned_as_responsible_user
from ..models import locations


@dataclasses.dataclass(frozen=True)
class LocationType:
    """
    This class provides an immutable wrapper around models.locations.LocationType.
    """
    id: int
    name: typing.Optional[typing.Dict[str, str]]
    location_name_singular: typing.Optional[typing.Dict[str, str]]
    location_name_plural: typing.Optional[typing.Dict[str, str]]
    admin_only: bool
    enable_parent_location: bool
    enable_sub_locations: bool
    enable_object_assignments: bool
    enable_responsible_users: bool
    enable_instruments: bool
    enable_capacities: bool
    show_location_log: bool
    fed_id: typing.Optional[int] = None
    component_id: typing.Optional[int] = None
    component: typing.Optional[Component] = None

    LOCATION = locations.LocationType.LOCATION

    @classmethod
    def from_database(cls, location_type: locations.LocationType) -> 'LocationType':
        return LocationType(
            id=location_type.id,
            name=location_type.name,
            location_name_singular=location_type.location_name_singular,
            location_name_plural=location_type.location_name_plural,
            admin_only=location_type.admin_only,
            enable_parent_location=location_type.enable_parent_location,
            enable_sub_locations=location_type.enable_sub_locations,
            enable_object_assignments=location_type.enable_object_assignments,
            enable_responsible_users=location_type.enable_responsible_users,
            enable_instruments=location_type.enable_instruments,
            enable_capacities=location_type.enable_capacities,
            show_location_log=location_type.show_location_log,
            fed_id=location_type.fed_id,
            component_id=location_type.component_id,
            component=Component.from_database(location_type.component) if location_type.component is not None else None
        )


@dataclasses.dataclass(frozen=True)
class Location:
    """
    This class provides an immutable wrapper around models.locations.Location.
    """
    id: int
    name: typing.Optional[typing.Dict[str, str]]
    description: typing.Optional[typing.Dict[str, str]]
    type_id: int
    type: LocationType
    responsible_users: typing.List[users.User]
    is_hidden: bool
    enable_object_assignments: bool
    topics: typing.List[topics.Topic]
    parent_location_id: typing.Optional[int] = None
    fed_id: typing.Optional[int] = None
    component_id: typing.Optional[int] = None
    component: typing.Optional[Component] = None

    @classmethod
    def from_database(cls, location: locations.Location) -> 'Location':
        return Location(
            id=location.id,
            name=location.name,
            description=location.description,
            parent_location_id=location.parent_location_id,
            fed_id=location.fed_id,
            component=Component.from_database(location.component) if location.component is not None else None,
            component_id=location.component_id,
            type_id=location.type_id,
            type=LocationType.from_database(location.type),
            responsible_users=[
                users.User.from_database(responsible_user)
                for responsible_user in location.responsible_users
            ],
            is_hidden=location.is_hidden,
            enable_object_assignments=location.enable_object_assignments,
            topics=[topics.Topic.from_database(topic) for topic in location.topics],
        )


@dataclasses.dataclass(frozen=True)
class ObjectLocationAssignment:
    """
    This class provides an immutable wrapper around models.locations.ObjectLocationAssignment.
    """
    id: int
    object_id: int
    location_id: typing.Optional[int]
    user_id: typing.Optional[int]
    description: typing.Optional[typing.Dict[str, str]]
    utc_datetime: typing.Optional[datetime.datetime]
    responsible_user_id: typing.Optional[int]
    confirmed: bool
    fed_id: typing.Optional[int] = None
    component_id: typing.Optional[int] = None
    declined: bool = False
    component: typing.Optional[Component] = None

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
            confirmed=object_location_assignment.confirmed,
            fed_id=object_location_assignment.fed_id,
            component_id=object_location_assignment.component_id,
            declined=object_location_assignment.declined,
            component=Component.from_database(object_location_assignment.component) if object_location_assignment.component is not None else None
        )


@typing.overload
def create_location(
        name: typing.Dict[str, str],
        description: typing.Dict[str, str],
        parent_location_id: typing.Optional[int],
        user_id: int,
        type_id: int,
        *,
        fed_id: None = None,
        component_id: None = None
) -> Location:
    ...


@typing.overload
def create_location(
        name: typing.Optional[typing.Dict[str, str]],
        description: typing.Optional[typing.Dict[str, str]],
        parent_location_id: typing.Optional[int],
        user_id: typing.Optional[int],
        type_id: int,
        *,
        fed_id: int,
        component_id: int
) -> Location:
    ...


def create_location(
        name: typing.Optional[typing.Dict[str, str]],
        description: typing.Optional[typing.Dict[str, str]],
        parent_location_id: typing.Optional[int],
        user_id: typing.Optional[int],
        type_id: int,
        *,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None
) -> Location:
    """
    Create a new location.

    :param name: the names for the new location in a dict. Keys are the language codes and values are the names.
    :param description: the descriptions for the new location.
        Keys are the language code and values are the descriptions.
    :param parent_location_id: the optional parent location ID for the new location
    :param user_id: the ID of an existing user
    :param fed_id: the federation ID of the location
    :param component_id: origin component ID
    :param type_id: the ID of an existing location type
    :return: the created location
    :raise errors.LocationDoesNotExistError: when no location with the given
        parent location ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.LocationTypeDoesNotExistError: when no location type with the
        given location type ID exists
    :raise errors.MissingEnglishTranslationError: when name does not contain
        an english translation
    """
    assert (component_id is None) == (fed_id is None)
    assert component_id is not None or (name is not None and description is not None and user_id is not None)

    if name is not None:
        if isinstance(name, str):
            name = {
                'en': name
            }
        assert isinstance(name, dict)
        if component_id is None:
            name = languages.filter_translations(name)

        # if a name is provided, there should be an english translation
        if 'en' not in name:
            raise errors.MissingEnglishTranslationError()

    if description is not None:
        if isinstance(description, str):
            description = {
                'en': description
            }
        assert isinstance(description, dict)
        if component_id is None:
            description = languages.filter_translations(description)

    # ensure the user exists
    if user_id is not None:
        users.check_user_exists(user_id)
    if parent_location_id is not None:
        # ensure parent location exists
        check_location_exists(parent_location_id)
    if component_id is not None:
        # ensure that the component can be found
        components.get_component(component_id)
    if type_id is not None:
        # ensure location type exists
        get_location_type(type_id)
    location = locations.Location(
        name=name,
        description=description,
        parent_location_id=parent_location_id,
        fed_id=fed_id,
        component_id=component_id,
        type_id=type_id
    )
    db.session.add(location)
    db.session.commit()
    if component_id is None:
        if user_id is not None:
            user_log.create_location(user_id, location.id)
    location_log.create_location(user_id, location.id)
    return Location.from_database(location)


def update_location(
        location_id: int,
        name: typing.Optional[typing.Dict[str, str]],
        description: typing.Optional[typing.Dict[str, str]],
        parent_location_id: typing.Optional[int],
        user_id: typing.Optional[int],
        type_id: int,
        is_hidden: bool,
        enable_object_assignments: bool,
) -> None:
    """
    Update a location's information.

    :param location_id: the ID of the location to update
    :param name: the new names for the location in a dict. Keys are the language codes and the values the new names
    :param description: the descriptions for the location.
        Keys are the language code and the values the new descriptions.
    :param parent_location_id: the optional parent location id for the location
    :param user_id: the ID of an existing user
    :param type_id: the ID of an existing location type
    :param is_hidden: whether the location is hidden
    :param enable_object_assignments: whether object assignments are enabled for the location
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID or parent location ID exists
    :raise errors.CyclicLocationError: when location ID is an ancestor of
        parent location ID
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.MissingEnglishTranslationError: if no english name is given
    :raise errors.LanguageDoesNotExistError: if an unknown language code is
        used
    :raise errors.LocationTypeDoesNotExistError: when no location type with the
        given location type ID exists
    """
    location = locations.Location.query.filter_by(id=location_id).first()
    if location is None:
        raise errors.LocationDoesNotExistError()

    if name is not None:
        assert isinstance(name, dict)
        if location.component_id is None:
            name = languages.filter_translations(name)

        # if a name is provided, there should be an english translation
        if 'en' not in name:
            raise errors.MissingEnglishTranslationError()

    if description is not None:
        assert isinstance(description, dict)
        if location.component_id is None:
            description = languages.filter_translations(description)

    # ensure the user exists
    if user_id is not None:
        users.check_user_exists(user_id)
    if parent_location_id is not None:
        if location_id == parent_location_id or location_id in _get_location_ancestors(parent_location_id):
            raise errors.CyclicLocationError()
    if type_id is not None:
        # ensure location type exists
        get_location_type(type_id)
    location.name = name
    location.description = description
    location.parent_location_id = parent_location_id
    location.type_id = type_id
    location.is_hidden = is_hidden
    location.enable_object_assignments = enable_object_assignments
    db.session.add(location)
    db.session.commit()
    if user_id is not None:
        user_log.update_location(user_id, location.id)
    location_log.update_location(user_id, location.id)


def check_location_exists(
        location_id: int
) -> None:
    """
    Check whether a location with the given location ID exists.

    :param location_id: the ID of an existing location
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    if not db.session.query(db.exists().where(locations.Location.id == location_id)).scalar():
        raise errors.LocationDoesNotExistError()


def get_location(location_id: int, component_id: typing.Optional[int] = None) -> Location:
    """
    Get a location.

    :param location_id: the ID of an existing location
    :param component_id: the ID of an existing component, or None
    :raise errors.LocationDoesNotExistError: when no location with the given
        ID exists
    :return: the location with the given location ID
    """
    if component_id is None:
        location = locations.Location.query.filter_by(id=location_id).first()
    else:
        location = locations.Location.query.filter_by(fed_id=location_id, component_id=component_id).first()
    if location is None:
        if component_id is not None:
            components.check_component_exists(component_id)
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
    locations_tree: typing.Dict[typing.Optional[int], typing.Any] = {}
    locations_tree_helper: typing.Dict[typing.Optional[int], typing.Any] = {None: locations_tree}
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


def is_full_location_tree_hidden(
    locations_map: typing.Dict[int, Location],
    locations_tree: typing.Any
) -> bool:
    """
    Return whether a full locations tree only contains hidden locations.

    :param locations_map: a dict mapping location IDs to locations
    :param locations_tree: the locations tree
    :return: whether all locations in the tree are hidden
    """
    return all(
        locations_map[location_id].is_hidden and is_full_location_tree_hidden(locations_map, locations_subtree)
        for location_id, locations_subtree in locations_tree.items()
        if location_id in locations_map
    )


def _get_location_ancestors(location_id: int) -> typing.List[int]:
    """
    Get the list of all ancestor location IDs.

    :param location_id: the ID of an existing location
    :return: the list of all ancestor location IDs
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    ancestor_location_ids = []
    ancestor_location_id: typing.Optional[int] = location_id
    while ancestor_location_id is not None:
        ancestor_location_ids.append(ancestor_location_id)
        ancestor_location_id = get_location(ancestor_location_id).parent_location_id
    return ancestor_location_ids[1:]


def assign_location_to_object(
        object_id: int,
        location_id: typing.Optional[int],
        responsible_user_id: typing.Optional[int],
        user_id: int,
        description: typing.Optional[typing.Dict[str, str]]
) -> None:
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
    :raise errors.ExceedingLocationCapacityError: when assigning the object
        to this location would exceed the location's capacity
    """

    if description is not None:
        if isinstance(description, str):
            description = {
                'en': description
            }
        assert isinstance(description, dict)
        description = languages.filter_translations(description)

    # ensure the object exists
    objects.check_object_exists(object_id)
    if location_id is not None:
        location = get_location(location_id)
        if location.type.enable_capacities:
            action_id = objects.get_object(object_id).action_id
            if action_id is None:
                raise errors.ExceedingLocationCapacityError()
            action_type_id = actions.get_action(action_id).type_id
            if action_type_id is None:
                raise errors.ExceedingLocationCapacityError()
            capacity = get_location_capacities(location_id).get(action_type_id, 0)
            if capacity is not None:
                if capacity == 0:
                    raise errors.ExceedingLocationCapacityError()
                num_stored_objects = get_assigned_object_count_by_action_types(
                    location_id,
                    ignored_object_ids=[object_id]
                ).get(action_type_id, 0)
                if num_stored_objects + 1 > capacity:
                    raise errors.ExceedingLocationCapacityError()
    # ensure the user exists
    users.check_user_exists(user_id)
    object_location_assignment = locations.ObjectLocationAssignment(
        object_id=object_id,
        location_id=location_id,
        responsible_user_id=responsible_user_id,
        user_id=user_id,
        description=description,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc),
        confirmed=(user_id == responsible_user_id),
        declined=False
    )
    db.session.add(object_location_assignment)
    db.session.commit()
    if responsible_user_id is not None:
        users.check_user_exists(responsible_user_id)
        if user_id != responsible_user_id:
            create_notification_for_being_assigned_as_responsible_user(object_location_assignment.id)
    object_log.assign_location(user_id, object_id, object_location_assignment.id)
    user_log.assign_location(user_id, object_location_assignment.id)
    previous_object_location_assignment = locations.ObjectLocationAssignment.query.filter_by(
        object_id=object_id
    ).order_by(
        db.desc(locations.ObjectLocationAssignment.utc_datetime)
    ).offset(1).first()
    if previous_object_location_assignment is not None:
        previous_location_id = previous_object_location_assignment.location_id
    else:
        previous_location_id = None
    if location_id is not None and location_id == previous_location_id:
        location_log.change_object(user_id, location_id, object_location_assignment.id)
    else:
        if location_id is not None:
            location_log.add_object(user_id, location_id, object_location_assignment.id)
        if previous_location_id is not None:
            location_log.remove_object(user_id, previous_location_id, object_location_assignment.id)


def create_fed_assignment(
        fed_id: int,
        component_id: int,
        object_id: int,
        location_id: typing.Optional[int],
        responsible_user_id: typing.Optional[int],
        user_id: typing.Optional[int],
        description: typing.Optional[typing.Dict[str, str]],
        utc_datetime: typing.Optional[datetime.datetime],
        confirmed: bool = False,
        declined: bool = False
) -> locations.ObjectLocationAssignment:
    if description is not None:
        if isinstance(description, str):
            description = {
                'en': description
            }
        assert isinstance(description, dict)
        description = languages.filter_translations(description)

    objects.check_object_exists(object_id)
    # ensure the component exists
    components.check_component_exists(component_id)
    if location_id is not None:
        # ensure the location exists
        check_location_exists(location_id)
    if user_id is not None:
        users.check_user_exists(user_id)
    if responsible_user_id is not None:
        users.check_user_exists(responsible_user_id)
    object_location_assignment = locations.ObjectLocationAssignment(
        object_id=object_id,
        location_id=location_id,
        responsible_user_id=responsible_user_id,
        user_id=user_id,
        description=description,
        utc_datetime=utc_datetime,
        confirmed=confirmed or False,
        declined=declined,
        fed_id=fed_id,
        component_id=component_id
    )
    db.session.add(object_location_assignment)
    db.session.commit()
    return object_location_assignment


def get_object_location_assignments(object_id: int) -> typing.List[ObjectLocationAssignment]:
    """
    Get a list of all object location assignments for an object.

    :param object_id: the ID of an existing object
    :return: the list of object location assignments
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    # ensure the object exists
    objects.check_object_exists(object_id)
    object_location_assignments = locations.ObjectLocationAssignment.query.filter_by(object_id=object_id).order_by(locations.ObjectLocationAssignment.utc_datetime).all()
    return [
        ObjectLocationAssignment.from_database(object_location_assignment)
        for object_location_assignment in object_location_assignments
    ]


def get_fed_object_location_assignment(fed_id: int, component_id: int) -> typing.Optional[locations.ObjectLocationAssignment]:
    object_location_assignment: typing.Optional[locations.ObjectLocationAssignment] = locations.ObjectLocationAssignment.query.filter_by(fed_id=fed_id, component_id=component_id).first()
    return object_location_assignment


def get_current_object_location_assignment(object_id: int) -> typing.Optional[ObjectLocationAssignment]:
    """
    Get the current location assignment for an object.

    :param object_id: the ID of an existing object
    :return: the object location assignment
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    # ensure the object exists
    objects.check_object_exists(object_id)
    object_location_assignment: typing.Optional[locations.ObjectLocationAssignment] = locations.ObjectLocationAssignment.query.filter_by(object_id=object_id).order_by(locations.ObjectLocationAssignment.utc_datetime.desc()).first()
    if object_location_assignment is None:
        return None
    return ObjectLocationAssignment.from_database(object_location_assignment)


def get_current_object_location_assignments(
        object_ids: typing.Sequence[int]
) -> typing.Mapping[int, typing.Optional[ObjectLocationAssignment]]:
    """
    Get the current location assignments for a list of objects.

    :param object_ids: a list of IDs of existing objects
    :return: a dict mapping object IDs to the object location assignments
    :raise errors.ObjectDoesNotExistError: when no object with one of the
        given object IDs exists
    """

    assignment_rows = locations.ObjectLocationAssignment.query.distinct(
        locations.ObjectLocationAssignment.object_id
    ).filter(
        locations.ObjectLocationAssignment.object_id.in_(object_ids)
    ).order_by(
        locations.ObjectLocationAssignment.object_id, locations.ObjectLocationAssignment.utc_datetime.desc()
    ).all()

    object_location_assignments: typing.Dict[int, typing.Optional[ObjectLocationAssignment]] = {}
    for assignment_row in assignment_rows:
        object_location_assignments[assignment_row.object_id] = ObjectLocationAssignment.from_database(assignment_row)
    for object_id in object_ids:
        if object_id not in object_location_assignments:
            objects.check_object_exists(object_id)
            object_location_assignments[object_id] = None
    return object_location_assignments


def _get_mutable_object_location_assignment(object_location_assignment_id: int) -> locations.ObjectLocationAssignment:
    """
    Get a mutable object location assignment with a given ID.

    :param object_location_assignment_id: the ID of an existing object location
        assignment
    :return: the mutable object location assignment
    :raise errors.ObjectLocationAssignmentDoesNotExistError: when no object
        location assignment with the given object location assignment ID exists
    """
    object_location_assignment = locations.ObjectLocationAssignment.query.filter_by(id=object_location_assignment_id).first()
    if object_location_assignment is None:
        raise errors.ObjectLocationAssignmentDoesNotExistError()
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
    return ObjectLocationAssignment.from_database(_get_mutable_object_location_assignment(object_location_assignment_id))


def any_objects_at_location(location_id: int) -> bool:
    """
    Get whether there are any objects currently assigned to a location.

    :param location_id: the ID of an existing location
    :return: whether there are any objects assigned to the location
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    # ensure the location exists
    check_location_exists(location_id)
    object_location_assignments = locations.ObjectLocationAssignment.query.filter_by(location_id=location_id).all()
    for object_location_assignment in object_location_assignments:
        object_id = object_location_assignment.object_id
        current_object_location_assignment = get_current_object_location_assignment(object_id)
        if current_object_location_assignment is not None and current_object_location_assignment.location_id == location_id:
            return True
    return False


def get_object_ids_at_location(location_id: int) -> typing.Set[int]:
    """
    Get a list of all objects currently assigned to a location.

    :param location_id: the ID of an existing location
    :return: the list of object IDs assigned to the location
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    # ensure the location exists
    check_location_exists(location_id)
    object_location_assignments = locations.ObjectLocationAssignment.query.filter_by(location_id=location_id).all()
    object_ids = set()
    for object_location_assignment in object_location_assignments:
        object_id = object_location_assignment.object_id
        current_object_location_assignment = get_current_object_location_assignment(object_id)
        if current_object_location_assignment is not None and current_object_location_assignment.location_id == location_id:
            object_ids.add(object_id)
    return object_ids


def confirm_object_responsibility(object_location_assignment_id: int) -> None:
    """
    Confirm an object location assignment.

    :param object_location_assignment_id: the ID of an existing object location
        assignment
    :raise errors.ObjectLocationAssignmentDoesNotExistError: when no object
        location assignment with the given object location assignment ID exists
    :raise errors.ObjectLocationAssignmentAlreadyDeclinedError: when the
        object location assignment has already been declined
    """
    object_location_assignment = _get_mutable_object_location_assignment(object_location_assignment_id)
    if object_location_assignment.declined:
        raise errors.ObjectLocationAssignmentAlreadyDeclinedError()
    object_location_assignment.confirmed = True
    db.session.add(object_location_assignment)
    db.session.commit()


def decline_object_responsibility(object_location_assignment_id: int) -> None:
    """
    Decline responsibility for an object.

    :param object_location_assignment_id: the ID of an existing object location
        assignment
    :raise errors.ObjectLocationAssignmentDoesNotExistError: when no object
        location assignment with the given object location assignment ID exists
    :raise errors.ObjectLocationAssignmentAlreadyConfirmedError: when the
        object location assignment has already been confirmed
    """
    object_location_assignment = _get_mutable_object_location_assignment(object_location_assignment_id)
    if object_location_assignment.confirmed:
        raise errors.ObjectLocationAssignmentAlreadyConfirmedError()
    object_location_assignment.declined = True
    db.session.add(object_location_assignment)
    db.session.commit()


def get_unhandled_object_responsibility_assignments(
        user_id: int
) -> typing.List[ObjectLocationAssignment]:
    """
    Get all object location assignments that assign responsibility to a given
    user and have not yet been confirmed or declined.

    :param user_id: the ID of an existing user
    :return: the object location assignments
    """
    object_location_assignments = locations.ObjectLocationAssignment.query.filter_by(
        responsible_user_id=user_id,
        confirmed=False,
        declined=False
    ).order_by(locations.ObjectLocationAssignment.utc_datetime.desc()).all()
    return [
        ObjectLocationAssignment.from_database(object_location_assignment)
        for object_location_assignment in object_location_assignments
    ]


def create_location_type(
        name: typing.Optional[typing.Dict[str, str]],
        location_name_singular: typing.Optional[typing.Dict[str, str]],
        location_name_plural: typing.Optional[typing.Dict[str, str]],
        admin_only: bool,
        enable_parent_location: bool,
        enable_sub_locations: bool,
        enable_object_assignments: bool,
        enable_responsible_users: bool,
        enable_instruments: bool,
        enable_capacities: bool,
        show_location_log: bool,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None
) -> LocationType:
    """
    Create a new location type.

    :param name: the names for the new location type in a dict. Keys are the
        language codes and values are the names.
    :param location_name_singular: the names for single locations of this type in a dict
    :param location_name_plural: the names for multiple locations of this type in a dict
    :param admin_only: whether only administrators can create locations of this type
    :param enable_parent_location: whether locations of this type may have a parent location
    :param enable_sub_locations: whether locations of this type may have sub locations
    :param enable_object_assignments: whether objects may be assigned to locations of this type
    :param enable_responsible_users: whether locations of this type may have responsible users
    :param enable_instruments: whether instruments may be assigned to locations of this type
    :param enable_capacities: whether locations of this type have capacities
    :param show_location_log: whether the location log should be shown for locations of this type
    :param fed_id: the federation ID of the location type
    :param component_id: origin component ID
    :return: the created location type
    """
    location_type = locations.LocationType(
        name=name,
        location_name_singular=location_name_singular,
        location_name_plural=location_name_plural,
        admin_only=admin_only,
        enable_parent_location=enable_parent_location,
        enable_sub_locations=enable_sub_locations,
        enable_object_assignments=enable_object_assignments,
        enable_responsible_users=enable_responsible_users,
        enable_instruments=enable_instruments,
        enable_capacities=enable_capacities,
        show_location_log=show_location_log,
        fed_id=fed_id,
        component_id=component_id
    )
    db.session.add(location_type)
    db.session.commit()
    return LocationType.from_database(location_type)


def update_location_type(
        location_type_id: int,
        name: typing.Optional[typing.Dict[str, str]],
        location_name_singular: typing.Optional[typing.Dict[str, str]],
        location_name_plural: typing.Optional[typing.Dict[str, str]],
        admin_only: bool,
        enable_parent_location: bool,
        enable_sub_locations: bool,
        enable_object_assignments: bool,
        enable_responsible_users: bool,
        enable_instruments: bool,
        enable_capacities: bool,
        show_location_log: bool,
) -> None:
    """
    Create a new location type.

    :param location_type_id: the ID of an existing location type
    :param name: the names for the new location type in a dict. Keys are the
        language codes and values are the names.
    :param location_name_singular: the names for single locations of this type in a dict
    :param location_name_plural: the names for multiple locations of this type in a dict
    :param admin_only: whether only administrators can create locations of this type
    :param enable_parent_location: whether locations of this type may have a parent location
    :param enable_sub_locations: whether locations of this type may have sub locations
    :param enable_object_assignments: whether objects may be assigned to locations of this type
    :param enable_responsible_users: whether locations of this type may have responsible users
    :param enable_instruments: whether instruments may be assigned to locations of this type
    :param enable_capacities: whether locations of this type have capacities
    :param show_location_log: whether the location log should be shown for locations of this type
    :raise errors.LocationTypeDoesNotExistError: if no location type with the
        given ID exists
    """
    location_type = locations.LocationType.query.filter_by(id=location_type_id).first()
    if location_type is None:
        raise errors.LocationTypeDoesNotExistError()
    location_type.name = name
    location_type.location_name_singular = location_name_singular
    location_type.location_name_plural = location_name_plural
    location_type.admin_only = admin_only
    location_type.enable_parent_location = enable_parent_location
    location_type.enable_sub_locations = enable_sub_locations
    location_type.enable_object_assignments = enable_object_assignments
    location_type.enable_responsible_users = enable_responsible_users
    location_type.enable_instruments = enable_instruments
    location_type.enable_capacities = enable_capacities
    location_type.show_location_log = show_location_log
    db.session.add(location_type)
    db.session.commit()


def get_location_type(
        location_type_id: int,
        component_id: typing.Optional[int] = None
) -> LocationType:
    """
    Get a location type.

    :param location_type_id: the ID of an existing location type
    :param component_id: the ID of an existing component, or None
    :raise errors.LocationTypeDoesNotExistError: when no location type with
        the given ID exists
    :return: the location type with the given location type ID
    """
    if component_id is None:
        location_type = locations.LocationType.query.filter_by(id=location_type_id).first()
    else:
        location_type = locations.LocationType.query.filter_by(fed_id=location_type_id, component_id=component_id).first()
    if location_type is None:
        if component_id is not None:
            components.check_component_exists(component_id)
        raise errors.LocationTypeDoesNotExistError()
    return LocationType.from_database(location_type)


def get_location_types() -> typing.List[LocationType]:
    """
    Get all location types.

    :return: the list of all location types
    """
    location_types = locations.LocationType.query.order_by(db.asc(locations.LocationType.id)).all()
    return [
        LocationType.from_database(location_type)
        for location_type in location_types
    ]


def set_location_responsible_users(
        location_id: int,
        responsible_user_ids: typing.List[int]
) -> None:
    """
    Set the responsible users for a location.

    :param location_id: the ID of an existing location
    :param responsible_user_ids: a list of user IDs
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    location = locations.Location.query.filter_by(id=location_id).first()
    if location is None:
        raise errors.LocationDoesNotExistError()
    location.responsible_users.clear()
    for user_id in responsible_user_ids:
        user = users.get_mutable_user(user_id)
        location.responsible_users.append(user)
    db.session.add(location)
    db.session.commit()


def get_descendent_location_ids(
        locations_tree: typing.Dict[typing.Optional[int], typing.Any]
) -> typing.Set[int]:
    location_tree_queue = [locations_tree]
    descendent_location_ids: typing.Set[int] = set()
    while location_tree_queue:
        locations_tree = location_tree_queue.pop()
        for child_location_id in locations_tree:
            if child_location_id is not None:
                descendent_location_ids.add(child_location_id)
                location_tree_queue.append(locations_tree[child_location_id])
    return descendent_location_ids


def get_location_capacities(
        location_id: int
) -> typing.Dict[int, typing.Optional[int]]:
    """
    Get the capacity by action type for a given location.

    :param location_id: the ID of an existing location
    :return: a dict mapping action type IDs to capacities
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    location_capacities = locations.LocationCapacity.query.filter_by(location_id=location_id).all()
    if not location_capacities:
        check_location_exists(location_id)
    return {
        location_capacity.action_type_id: location_capacity.capacity
        for location_capacity in location_capacities
    }


def set_location_capacity(
        location_id: int,
        action_type_id: int,
        capacity: typing.Optional[int]
) -> None:
    """
    Set the capacity for objects of a given action type at a given location.

    :param location_id: the ID of an existing location
    :param action_type_id: the ID of an existing action type
    :param capacity: the storage capacity, or None for unlimited capacity
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    check_location_exists(location_id)
    check_action_type_exists(action_type_id)
    if capacity is not None and capacity < 0:
        capacity = 0
    location_capacity = locations.LocationCapacity.query.filter_by(location_id=location_id, action_type_id=action_type_id).first()
    if capacity == 0:
        if location_capacity is not None:
            db.session.delete(location_capacity)
    else:
        if location_capacity is None:
            location_capacity = locations.LocationCapacity(
                location_id=location_id,
                action_type_id=action_type_id,
                capacity=capacity
            )
        else:
            location_capacity.capacity = capacity
        db.session.add(location_capacity)
    db.session.commit()


def clear_location_capacities(
        location_id: int
) -> None:
    """
    Set the capacity for objects of any action type at a given location to 0.

    :param location_id: the ID of an existing location
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    check_location_exists(location_id)
    location_capacities = locations.LocationCapacity.query.filter_by(location_id=location_id).all()
    if location_capacities:
        for location_capacity in location_capacities:
            db.session.delete(location_capacity)
        db.session.commit()
    else:
        check_location_exists(location_id)


def get_assigned_object_count_by_action_types(  # pylint: disable=useless-param-doc
        location_id: int,
        ignored_object_ids: typing.Sequence[int] = ()
) -> typing.Dict[int, int]:
    """
    Get the amount of objects (by action type) assigned to a given location.

    :param location_id: the ID of an existing location
    :param ignored_object_ids: a list of object IDs to ignore
    :return: a dict mapping action type IDs to object counts
    :raise errors.LocationDoesNotExistError: when no location with the given
        location ID exists
    """
    # location -> objects
    location_assignments = locations.ObjectLocationAssignment.query.filter_by(
        location_id=location_id
    ).filter(
        db.not_(locations.ObjectLocationAssignment.object_id.in_(ignored_object_ids))
    ).subquery('location_assignments')
    current_location_assignments = locations.ObjectLocationAssignment.query.distinct(
        locations.ObjectLocationAssignment.object_id
    ).filter(
        locations.ObjectLocationAssignment.object_id == location_assignments.c.object_id
    ).order_by(
        locations.ObjectLocationAssignment.object_id,
        locations.ObjectLocationAssignment.utc_datetime.desc()
    ).all()
    current_location_assignments = [
        location_assignment
        for location_assignment in current_location_assignments
        if location_assignment.location_id == location_id
    ]
    if not current_location_assignments:
        check_location_exists(location_id)
        return {}
    # objects -> actions
    stored_object_ids = [
        a.object_id for a in current_location_assignments
    ]
    action_ids_for_object_ids = logic.objects.get_action_ids_for_object_ids(stored_object_ids)
    # actions -> action types
    stored_action_ids = [
        typing.cast(int, action_ids_for_object_ids[object_id])
        for object_id in stored_object_ids
        if action_ids_for_object_ids.get(object_id) is not None
    ]
    action_type_ids_for_action_ids = logic.actions.get_action_type_ids_for_action_ids(stored_action_ids)
    # action types -> fed action types
    stored_action_type_ids = set(action_type_ids_for_action_ids.values())
    action_type_ids_and_fed_action_type_ids = models.actions.ActionType.query.with_entities(
        models.actions.ActionType.id,
        models.actions.ActionType.fed_id
    ).filter(
        models.actions.ActionType.fed_id.is_not(None),
        models.actions.ActionType.fed_id < 0,
        models.actions.ActionType.id.in_(stored_action_type_ids)
    ).all()
    fed_action_type_ids_for_action_type_ids = {
        action_type_id: fed_action_type_id
        for action_type_id, fed_action_type_id in action_type_ids_and_fed_action_type_ids
    }
    # location -> action types
    result = {}
    for object_id in stored_object_ids:
        action_id = action_ids_for_object_ids.get(object_id)
        if action_id is None:
            continue
        action_type_id = action_type_ids_for_action_ids.get(action_id)
        if action_type_id is None:
            continue
        action_type_id = fed_action_type_ids_for_action_type_ids.get(action_type_id, action_type_id)
        if action_type_id is None:
            continue
        if action_type_id not in result:
            result[action_type_id] = 0
        result[action_type_id] += 1
    return result
