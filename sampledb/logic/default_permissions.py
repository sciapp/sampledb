import typing

from . import users
from .permissions import ResourcePermissions
from .errors import InvalidDefaultPermissionsError
from ..models import Permissions, DefaultUserPermissions, DefaultGroupPermissions, DefaultProjectPermissions, AllUserDefaultPermissions

default_permissions = ResourcePermissions(
    resource_id_name='creator_id',
    all_user_permissions_table=AllUserDefaultPermissions,
    anonymous_user_permissions_table=None,
    user_permissions_table=DefaultUserPermissions,
    group_permissions_table=DefaultGroupPermissions,
    project_permissions_table=DefaultProjectPermissions,
    check_resource_exists=lambda resource_id: users.check_user_exists(user_id=resource_id)  # type: ignore
)


def get_default_permissions_for_users(creator_id: int) -> typing.Dict[int, Permissions]:
    # the creator always has GRANT as default permissions
    additional_permissions = {
        creator_id: Permissions.GRANT
    }
    return default_permissions.get_permissions_for_users(
        resource_id=creator_id,
        additional_permissions=additional_permissions
    )


def set_default_permissions_for_user(creator_id: int, user_id: int, permissions: Permissions) -> None:
    if user_id == creator_id:
        if permissions == Permissions.GRANT:
            return None
        else:
            raise InvalidDefaultPermissionsError("creator will always get GRANT permissions")
    return default_permissions.set_permissions_for_user(
        resource_id=creator_id,
        user_id=user_id,
        permissions=permissions
    )


def get_default_permissions_for_groups(creator_id: int) -> typing.Dict[int, Permissions]:
    return default_permissions.get_permissions_for_groups(resource_id=creator_id)


def set_default_permissions_for_group(creator_id: int, group_id: int, permissions: Permissions) -> None:
    default_permissions.set_permissions_for_group(
        resource_id=creator_id,
        group_id=group_id,
        permissions=permissions
    )


def get_default_permissions_for_projects(creator_id: int) -> typing.Dict[int, Permissions]:
    return default_permissions.get_permissions_for_projects(resource_id=creator_id)


def set_default_permissions_for_project(creator_id: int, project_id: int, permissions: Permissions) -> None:
    default_permissions.set_permissions_for_project(
        resource_id=creator_id,
        project_id=project_id,
        permissions=permissions
    )


def get_default_permissions_for_all_users(creator_id: int) -> Permissions:
    return default_permissions.get_permissions_for_all_users(resource_id=creator_id)


def set_default_permissions_for_all_users(creator_id: int, permissions: Permissions) -> None:
    return default_permissions.set_permissions_for_all_users(resource_id=creator_id, permissions=permissions)


def get_default_permissions_for_anonymous_users(creator_id: int) -> Permissions:
    return default_permissions.get_permissions_for_anonymous_users(resource_id=creator_id)
