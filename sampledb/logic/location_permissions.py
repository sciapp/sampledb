# coding: utf-8
"""

"""

import typing

import flask

from . import locations, users
from ..models import Permissions, AllUserLocationPermissions, UserLocationPermissions, GroupLocationPermissions, ProjectLocationPermissions
from .permissions import ResourcePermissions


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


location_permissions = ResourcePermissions(
    resource_id_name='location_id',
    all_user_permissions_table=AllUserLocationPermissions,
    anonymous_user_permissions_table=None,
    user_permissions_table=UserLocationPermissions,
    group_permissions_table=GroupLocationPermissions,
    project_permissions_table=ProjectLocationPermissions,
    check_resource_exists=lambda resource_id: locations.get_location(location_id=resource_id)
)


def get_user_location_permissions(
        location_id,
        user_id,
        *,
        include_groups: bool = True,
        include_projects: bool = True,
        include_admin_permissions: bool = True
) -> Permissions:
    additional_permissions = Permissions.NONE
    if user_id is None:
        return Permissions.NONE

    user = users.get_user(user_id)
    if user.is_readonly:
        max_permissions = Permissions.READ
    else:
        max_permissions = Permissions.GRANT

    if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS']:
        # if only admins are allowed to manage locations, only they can have
        # more than READ permissions
        if not (include_admin_permissions and user.has_admin_permissions):
            max_permissions = min(max_permissions, Permissions.READ)

    # resource independent permissions
    permissions = location_permissions.get_permissions_for_user(
        resource_id=location_id,
        user_id=user_id,
        include_all_users=True,
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions,
        limit_readonly_users=False,
        additional_permissions=additional_permissions
    )
    return min(permissions, max_permissions)


def get_location_permissions_for_all_users(location_id: int) -> Permissions:
    return location_permissions.get_permissions_for_all_users(resource_id=location_id)


def set_location_permissions_for_all_users(location_id: int, permissions: Permissions) -> None:
    location_permissions.set_permissions_for_all_users(resource_id=location_id, permissions=permissions)


def get_location_permissions_for_users(location_id) -> typing.Dict[int, Permissions]:
    return location_permissions.get_permissions_for_users(resource_id=location_id)


def set_user_location_permissions(location_id: int, user_id: int, permissions: Permissions):
    location_permissions.set_permissions_for_user(resource_id=location_id, user_id=user_id, permissions=permissions)


def get_location_permissions_for_groups(location_id: int) -> typing.Dict[int, Permissions]:
    return location_permissions.get_permissions_for_groups(resource_id=location_id)


def set_group_location_permissions(location_id: int, group_id: int, permissions: Permissions):
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
    user = users.get_user(user_id)
    if permissions not in Permissions.READ:
        if user.is_readonly:
            return []
        if not user.is_admin and flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS']:
            return []
    locations_with_user_permissions = []
    for location in all_locations:
        if permissions in get_user_location_permissions(location.id, user_id):
            locations_with_user_permissions.append(location)
    return locations_with_user_permissions
