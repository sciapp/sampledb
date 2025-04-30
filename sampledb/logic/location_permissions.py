# coding: utf-8
"""

"""

import typing

import flask

from . import locations, users
from ..models import Permissions, AllUserLocationPermissions, UserLocationPermissions, GroupLocationPermissions, ProjectLocationPermissions
from ..models.locations import location_user_association_table
from .permissions import ResourcePermissions
from .. import db


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


location_permissions = ResourcePermissions(
    resource_id_name='location_id',
    all_user_permissions_table=AllUserLocationPermissions,
    anonymous_user_permissions_table=None,
    user_permissions_table=UserLocationPermissions,
    group_permissions_table=GroupLocationPermissions,
    project_permissions_table=ProjectLocationPermissions,
    check_resource_exists=lambda resource_id: locations.check_location_exists(location_id=resource_id)
)


def get_user_location_permissions(
        location_id: int,
        user_id: typing.Optional[int],
        *,
        include_groups: bool = True,
        include_projects: bool = True,
        include_admin_permissions: bool = True
) -> Permissions:
    return get_user_permissions_for_multiple_locations(
        user_id=user_id,
        location_ids=[location_id],
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions
    )[location_id]


def get_user_permissions_for_multiple_locations(
        location_ids: typing.Sequence[int],
        user_id: typing.Optional[int],
        *,
        include_groups: bool = True,
        include_projects: bool = True,
        include_admin_permissions: bool = True,
        max_permissions: Permissions = Permissions.GRANT
) -> typing.Mapping[int, Permissions]:
    if not location_ids:
        return {}

    additional_permissions = {
        location_id: Permissions.NONE
        for location_id in location_ids
    }
    if user_id is None:
        return {
            location_id: Permissions.NONE
            for location_id in location_ids
        }

    if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS']:
        user = users.get_user(user_id)
        # if only admins are allowed to manage locations, only they can have
        # more than READ permissions
        if not (include_admin_permissions and user.has_admin_permissions):
            max_permissions = min(max_permissions, Permissions.READ)

    for location_id in location_ids:
        # apply responsible user permissions
        if bool(db.session.query(db.exists().where(location_user_association_table.c.location_id == location_id, location_user_association_table.c.user_id == user_id)).scalar()):
            additional_permissions[location_id] = min(Permissions.GRANT, max_permissions)

    # resource independent permissions
    return location_permissions.get_permissions_for_user_for_multiple_resources(
        resource_ids=location_ids,
        user_id=user_id,
        include_all_users=True,
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions,
        limit_readonly_users=True,
        additional_permissions=additional_permissions,
        max_permissions=max_permissions
    )


def get_location_permissions_for_all_users(location_id: int) -> Permissions:
    return location_permissions.get_permissions_for_all_users(resource_id=location_id)


def set_location_permissions_for_all_users(location_id: int, permissions: Permissions) -> None:
    location_permissions.set_permissions_for_all_users(resource_id=location_id, permissions=permissions)


def get_location_permissions_for_users(location_id: int) -> typing.Dict[int, Permissions]:
    return location_permissions.get_permissions_for_users(resource_id=location_id)


def set_user_location_permissions(location_id: int, user_id: int, permissions: Permissions) -> None:
    location_permissions.set_permissions_for_user(resource_id=location_id, user_id=user_id, permissions=permissions)


def get_location_permissions_for_groups(location_id: int) -> typing.Dict[int, Permissions]:
    return location_permissions.get_permissions_for_groups(resource_id=location_id)


def set_group_location_permissions(location_id: int, group_id: int, permissions: Permissions) -> None:
    location_permissions.set_permissions_for_group(resource_id=location_id, group_id=group_id, permissions=permissions)


def get_location_permissions_for_projects(location_id: int) -> typing.Dict[int, Permissions]:
    return location_permissions.get_permissions_for_projects(resource_id=location_id)


def set_project_location_permissions(location_id: int, project_id: int, permissions: Permissions) -> None:
    location_permissions.set_permissions_for_project(resource_id=location_id, project_id=project_id, permissions=permissions)


def get_locations_with_user_permissions(
        user_id: typing.Optional[int],
        permissions: Permissions
) -> typing.List['locations.Location']:
    if user_id is None:
        return []

    all_locations = locations.get_locations()
    if permissions in Permissions.NONE:
        return all_locations
    if permissions not in Permissions.READ:
        user = users.get_user(user_id)
        if user.is_readonly:
            return []
        if not user.is_admin and flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS']:
            return []
    location_permissions = get_user_permissions_for_multiple_locations(
        location_ids=[location.id for location in all_locations],
        user_id=user_id,
        max_permissions=permissions
    )
    locations_with_user_permissions = []
    for location in all_locations:
        if permissions in location_permissions[location.id]:
            locations_with_user_permissions.append(location)
    return locations_with_user_permissions


def location_is_public(location_id: int) -> bool:
    """
    Returns whether a location is public.

    A location is considered public if its permission settings match those set
    for locations created as public via the frontend, i.e. WRITE permissions
    for all users and no explicitly set permissions for users, groups or
    projects.

    :param location_id: the id of the location
    :return: whether the location is public
    :raise errors.LocationDoesNotExistError: if no location with the given ID
        exists
    """
    if get_location_permissions_for_all_users(location_id) != Permissions.WRITE:
        return False

    if db.session.query(db.exists().where(UserLocationPermissions.location_id == location_id)).scalar():
        return False
    if db.session.query(db.exists().where(GroupLocationPermissions.location_id == location_id)).scalar():
        return False
    if db.session.query(db.exists().where(ProjectLocationPermissions.location_id == location_id)).scalar():
        return False
    locations.check_location_exists(location_id)
    return True
