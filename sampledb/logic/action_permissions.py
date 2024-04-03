# coding: utf-8
"""

"""

import typing

import flask

from . import actions
from . import users
from .permissions import ResourcePermissions
from .actions import Action
from ..models import Permissions, UserActionPermissions, GroupActionPermissions, ProjectActionPermissions, AllUserActionPermissions
from ..models.instruments import instrument_user_association_table
from .. import db, models

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
    return get_user_permissions_for_multiple_actions(
        action_ids=[action_id],
        user_id=user_id,
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions,
        include_instrument_responsible_users=include_instrument_responsible_users
    )[action_id]


def get_user_permissions_for_multiple_actions(
        action_ids: typing.Sequence[int],
        user_id: typing.Optional[int],
        *,
        include_groups: bool = True,
        include_projects: bool = True,
        include_admin_permissions: bool = True,
        include_instrument_responsible_users: bool = True,
        max_permissions: Permissions = Permissions.GRANT
) -> typing.Mapping[int, Permissions]:
    if not action_ids:
        return {}

    if user_id is None:
        return {
            action_id: Permissions.NONE
            for action_id in action_ids
        }

    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        include_instrument_responsible_users = False

    additional_permissions = {
        action_id: Permissions.NONE
        for action_id in action_ids
    }

    for action_id in action_ids:
        # users have GRANT permissions for actions they own
        owner_id = actions.get_action_owner_id(action_id)
        if owner_id is not None and owner_id == user_id:
            additional_permissions[action_id] = Permissions.GRANT

    if include_instrument_responsible_users:
        # instrument responsible users have GRANT permissions for actions of their instrument
        user_is_instrument_responsible = _is_user_responsible_for_actions_instruments(
            user_id=user_id,
            action_ids=[
                action_id
                for action_id in action_ids
                if Permissions.GRANT not in additional_permissions[action_id]
            ]
        )
        for action_id in user_is_instrument_responsible:
            if user_is_instrument_responsible[action_id]:
                additional_permissions[action_id] = max(additional_permissions[action_id], Permissions.GRANT)

    # resource independent permissions
    return action_permissions.get_permissions_for_user_for_multiple_resources(
        resource_ids=action_ids,
        user_id=user_id,
        include_all_users=True,
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions,
        limit_readonly_users=True,
        additional_permissions=additional_permissions,
        max_permissions=max_permissions
    )


def _is_user_responsible_for_actions_instruments(
        user_id: int,
        action_ids: typing.Sequence[int]
) -> typing.Mapping[int, bool]:
    responsible_action_id_rows = db.session.query(models.Action.id).filter(
        models.Action.id.in_(tuple(action_ids)),
        models.Action.instrument_id == instrument_user_association_table.c.instrument_id,
        instrument_user_association_table.c.user_id == user_id
    ).all()
    return {
        action_id: (action_id,) in responsible_action_id_rows
        for action_id in action_ids
    }


def get_actions_with_permissions(user_id: typing.Optional[int], permissions: Permissions, action_type_id: typing.Optional[int] = None) -> typing.List[Action]:
    """
    Get all actions which a user has the given permissions for.

    Return an empty list if called with Permissions.NONE.

    :param user_id: the ID of an existing user, or None
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
    if user_id is not None:
        # ensure that the user can be found
        users.check_user_exists(user_id)
    if permissions == Permissions.NONE:
        return []
    all_actions = actions.get_actions(action_type_id=action_type_id)
    action_permissions = get_user_permissions_for_multiple_actions(
        action_ids=[action.id for action in all_actions],
        user_id=user_id,
        max_permissions=permissions
    )
    actions_with_permissions = []
    for action in all_actions:
        if permissions in action_permissions.get(action.id, Permissions.NONE):
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
    possibly_visible_actions = []
    for action in actions.get_actions(
        action_type_id=action_type_id
    ):
        if owner_id is not None and action.user_id != owner_id:
            continue
        if not include_hidden_actions and action.is_hidden and not user.is_admin and owner_id != user_id:
            continue
        possibly_visible_actions.append(action)
    visible_actions = []
    action_permissions = {}
    permissions = get_user_permissions_for_multiple_actions(
        user_id=user_id,
        action_ids=[action.id for action in possibly_visible_actions],
        max_permissions=Permissions.READ
    )
    for action in possibly_visible_actions:
        if Permissions.READ in permissions[action.id]:
            visible_actions.append(action)
            action_permissions[action.id] = permissions[action.id]
    return actions.sort_actions_for_user(actions=visible_actions, user_id=user_id)
