import typing

from .. import db
from .errors import InvalidDefaultPermissionsError
from ..models import Permissions, DefaultUserPermissions, DefaultGroupPermissions, DefaultProjectPermissions, AllUserDefaultPermissions


def get_default_permissions_for_users(creator_id: int) -> typing.Dict[int, Permissions]:
    default_permissions = {}
    for user_permissions in DefaultUserPermissions.query.filter_by(creator_id=creator_id).all():
        if user_permissions.permissions != Permissions.NONE:
            default_permissions[user_permissions.user_id] = user_permissions.permissions
    default_permissions[creator_id] = Permissions.GRANT
    return default_permissions


def set_default_permissions_for_user(creator_id: int, user_id: int, permissions: Permissions) -> None:
    if user_id == creator_id:
        if permissions == Permissions.GRANT:
            return
        else:
            raise InvalidDefaultPermissionsError("creator will always get GRANT permissions")
    user_permissions = DefaultUserPermissions.query.filter_by(creator_id=creator_id, user_id=user_id).first()
    if user_permissions is None:
        user_permissions = DefaultUserPermissions(creator_id=creator_id, user_id=user_id, permissions=permissions)
    else:
        user_permissions.permissions = permissions
    db.session.add(user_permissions)
    db.session.commit()


def get_default_permissions_for_groups(creator_id: int) -> typing.Dict[int, Permissions]:
    default_permissions = {}
    for group_permissions in DefaultGroupPermissions.query.filter_by(creator_id=creator_id).all():
        if group_permissions.permissions != Permissions.NONE:
            default_permissions[group_permissions.group_id] = group_permissions.permissions
    return default_permissions


def set_default_permissions_for_group(creator_id: int, group_id: int, permissions: Permissions) -> None:
    group_permissions = DefaultGroupPermissions.query.filter_by(creator_id=creator_id, group_id=group_id).first()
    if group_permissions is None:
        group_permissions = DefaultGroupPermissions(creator_id=creator_id, group_id=group_id, permissions=permissions)
    else:
        group_permissions.permissions = permissions
    db.session.add(group_permissions)
    db.session.commit()


def get_default_permissions_for_projects(creator_id: int) -> typing.Dict[int, Permissions]:
    default_permissions = {}
    for project_permissions in DefaultProjectPermissions.query.filter_by(creator_id=creator_id).all():
        if project_permissions.permissions != Permissions.NONE:
            default_permissions[project_permissions.project_id] = project_permissions.permissions
    return default_permissions


def set_default_permissions_for_project(creator_id: int, project_id: int, permissions: Permissions) -> None:
    project_permissions = DefaultProjectPermissions.query.filter_by(creator_id=creator_id, project_id=project_id).first()
    if project_permissions is None:
        project_permissions = DefaultProjectPermissions(creator_id=creator_id, project_id=project_id, permissions=permissions)
    else:
        project_permissions.permissions = permissions
    db.session.add(project_permissions)
    db.session.commit()


def default_is_public(creator_id: int) -> bool:
    public_permissions = AllUserDefaultPermissions.query.filter_by(creator_id=creator_id).first()
    if public_permissions is None:
        return False
    return Permissions.READ in public_permissions.permissions


def set_default_public(creator_id: int, is_public: bool = True) -> None:
    if is_public:
        public_permissions = AllUserDefaultPermissions.query.filter_by(creator_id=creator_id).first()
        if public_permissions is None:
            public_permissions = AllUserDefaultPermissions(creator_id=creator_id, permissions=Permissions.READ)
        else:
            public_permissions.permissions = Permissions.READ
        db.session.add(public_permissions)
    else:
        AllUserDefaultPermissions.query.filter_by(creator_id=creator_id).delete()
    db.session.commit()
