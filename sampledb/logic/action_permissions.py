# coding: utf-8
"""

"""

import typing

import flask

from . import actions
from . import favorites
from . import users
from .permissions import ResourcePermissions
from .actions import Action
from ..models import Permissions, UserActionPermissions, GroupActionPermissions, ProjectActionPermissions, AllUserActionPermissions
from ..models.instruments import instrument_user_association_table
from .. import db, models
from .utils import get_translated_text

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


action_permissions = ResourcePermissions(
    resource_id_name='action_id',
    all_user_permissions_table=AllUserActionPermissions,
    anonymous_user_permissions_table=None,
    user_permissions_table=UserActionPermissions,
    group_permissions_table=GroupActionPermissions,
    project_permissions_table=ProjectActionPermissions,
    check_resource_exists=lambda resource_id: actions.check_action_exists(action_id=resource_id)
)


def get_action_permissions_for_all_users(action_id: int) -> Permissions:
    return action_permissions.get_permissions_for_all_users(resource_id=action_id)


def set_action_permissions_for_all_users(action_id: int, permissions: Permissions) -> None:
    action_permissions.set_permissions_for_all_users(resource_id=action_id, permissions=permissions)


def get_action_permissions_for_users(action_id: int) -> typing.Dict[int, Permissions]:
    return action_permissions.get_permissions_for_users(resource_id=action_id)


def set_user_action_permissions(action_id: int, user_id: int, permissions: Permissions) -> None:
    action_permissions.set_permissions_for_user(resource_id=action_id, user_id=user_id, permissions=permissions)


def get_action_permissions_for_groups(action_id: int) -> typing.Dict[int, Permissions]:
    return action_permissions.get_permissions_for_groups(resource_id=action_id)


def set_group_action_permissions(action_id: int, group_id: int, permissions: Permissions) -> None:
    action_permissions.set_permissions_for_group(resource_id=action_id, group_id=group_id, permissions=permissions)


def get_action_permissions_for_projects(action_id: int) -> typing.Dict[int, Permissions]:
    return action_permissions.get_permissions_for_projects(resource_id=action_id)


def set_project_action_permissions(action_id: int, project_id: int, permissions: Permissions) -> None:
    action_permissions.set_permissions_for_project(resource_id=action_id, project_id=project_id, permissions=permissions)


def get_user_action_permissions(
        action_id: int,
        user_id: typing.Optional[int],
        *,
        include_groups: bool = True,
        include_projects: bool = True,
        include_admin_permissions: bool = True,
        include_instrument_responsible_users: bool = True
) -> Permissions:
    if user_id is None:
        return Permissions.NONE

    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        include_instrument_responsible_users = False

    additional_permissions = Permissions.NONE

    # users have GRANT permissions for actions they own
    owner_id = actions.get_action_owner_id(action_id)
    if owner_id is not None and owner_id == user_id:
        additional_permissions = Permissions.GRANT

    if Permissions.GRANT not in additional_permissions and include_instrument_responsible_users:
        # instrument responsible users have GRANT permissions for actions of their instrument
        if _is_user_responsible_for_action_instrument(user_id, action_id):
            additional_permissions = max(additional_permissions, Permissions.GRANT)

    # resource independent permissions
    return action_permissions.get_permissions_for_user(
        resource_id=action_id,
        user_id=user_id,
        include_all_users=True,
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions,
        limit_readonly_users=True,
        additional_permissions=additional_permissions
    )


def _is_user_responsible_for_action_instrument(
        user_id: int,
        action_id: int
) -> bool:
    return bool(db.session.query(
        db.exists().where(
            models.Action.id == action_id,
            models.Action.instrument_id == instrument_user_association_table.c.instrument_id,
            instrument_user_association_table.c.user_id == user_id
        )
    ).scalar())  # type: ignore


def get_actions_with_permissions(user_id: int, permissions: Permissions, action_type_id: typing.Optional[int] = None) -> typing.List[Action]:
    """
    Get all actions which a user has the given permissions for.

    Return an empty list if called with Permissions.NONE.

    :param user_id: the ID of an existing user
    :param permissions: the minimum permissions required for the actions for
        the given user
    :param action_type_id: None or the ID of an existing action type
    :return: the actions with the given permissions for the given
        user
    :raise errors.UserDoesNotExistError: if no user with the given user ID
        exists
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    # ensure that the user can be found
    users.check_user_exists(user_id)
    if permissions == Permissions.NONE:
        return []
    actions_with_permissions = []
    for action in actions.get_actions(action_type_id=action_type_id):
        if permissions in get_user_action_permissions(user_id=user_id, action_id=action.id):
            actions_with_permissions.append(action)
    return actions_with_permissions


def get_sorted_actions_for_user(
        user_id: int,
        action_type_id: typing.Optional[int] = None,
        owner_id: typing.Optional[int] = None,
        include_hidden_actions: bool = False
) -> typing.List[Action]:
    """
    Get sorted actions for a user, optionally filtered by type and owning user.

    The actions are sorted by:
    - favorite / not favorite
    - instrument name (independent actions first)
    - action name

    :param user_id: the ID of the user to return actions for
    :param action_type_id: the ID of the actions' type, or None
    :param owner_id: the ID of the actions' owner, or None
    :param include_hidden_actions: whether hidden actions should be included
    :return: the sorted list of actions
    :raise errors.UserDoesNotExistError: if no user with the given user ID
        exists
    """
    user = users.get_user(user_id)
    visible_actions = []
    action_permissions = {}
    for action in actions.get_actions(
        action_type_id=action_type_id
    ):
        if owner_id is not None and action.user_id != owner_id:
            continue
        if not include_hidden_actions and action.is_hidden and not user.is_admin and owner_id != user_id:
            continue
        permissions = get_user_action_permissions(user_id=user_id, action_id=action.id)
        if Permissions.READ in permissions:
            visible_actions.append(action)
            action_permissions[action.id] = permissions
    user_favorite_action_ids = favorites.get_user_favorite_action_ids(user_id)
    visible_actions.sort(key=lambda action: (
        0 if action.id in user_favorite_action_ids else 1,
        action.user.name.lower() if action.user and action.user.name is not None else '',
        get_translated_text(action.instrument.name).lower() if action.instrument else '',
        get_translated_text(action.name).lower()
    ))
    return visible_actions
