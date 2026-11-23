# coding: utf-8
"""

"""

import typing

import flask
import sqlalchemy

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
    resource_id_column=models.Action.__table__.c.id,
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


def _build_additional_queries(
        user_id: int,
        include_instrument_responsible_users: bool,
        action_id_filter: typing.Callable[[sqlalchemy.ColumnElement[int]], sqlalchemy.ColumnElement[bool]],
) -> list[sqlalchemy.Select[int, Permissions]]:
    additional_permissions_queries = []

    action_id_column = models.Action.__table__.c.id

    action_owner_query = db.select(
        action_id_column.label("action_id"),
        db.cast(Permissions.GRANT, models.UserActionPermissions.permissions.type).label("permissions")
    ).where(
        models.Action.user_id == user_id,
        action_id_filter(action_id_column)
    )
    additional_permissions_queries.append(action_owner_query)

    if include_instrument_responsible_users:
        instrument_responsible_user_query = db.select(
            action_id_column.label("action_id"),
            db.cast(Permissions.GRANT, models.UserActionPermissions.permissions.type).label("permissions")
        ).where(
            models.Action.instrument_id == instrument_user_association_table.c.instrument_id,
            instrument_user_association_table.c.user_id == user_id,
            action_id_filter(action_id_column)
        )
        additional_permissions_queries.append(instrument_responsible_user_query)

    return additional_permissions_queries


def get_permissions_query(
        action_ids: typing.Optional[typing.Sequence[int]],
        user_id: int,
        *,
        include_groups: bool = True,
        include_projects: bool = True,
        include_admin_permissions: bool = True,
        include_instrument_responsible_users: bool = True,
        max_permissions: Permissions = Permissions.GRANT
) -> sqlalchemy.Select[int, Permissions]:

    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        include_instrument_responsible_users = False

    if action_ids:
        def resource_id_filter(resource_id_column: sqlalchemy.ColumnElement[int]) -> sqlalchemy.ColumnElement[bool]:
            return resource_id_column.in_(action_ids)
    else:
        def resource_id_filter(resource_id_column: sqlalchemy.ColumnElement[int]) -> sqlalchemy.ColumnElement[bool]:
            return sqlalchemy.true()
    return action_permissions.get_combined_permissions_query(
        resource_id_filter=resource_id_filter,
        user_id=user_id,
        include_all_users=True,
        include_anonymous_users=False,
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions,
        limit_readonly_users=True,
        additional_permissions_queries=_build_additional_queries(
            user_id=user_id,
            include_instrument_responsible_users=include_instrument_responsible_users,
            action_id_filter=resource_id_filter,
        ),
        max_permissions=max_permissions,
    )


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
        # actions do not have permissions for anonymous users at this time
        return {
            action_id: Permissions.NONE
            for action_id in action_ids
        }

    permissions_query = get_permissions_query(
        action_ids=action_ids,
        user_id=user_id,
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions,
        include_instrument_responsible_users=include_instrument_responsible_users,
        max_permissions=max_permissions,
    )
    return {
        resource_id: permissions_from_row
        for resource_id, permissions_from_row in db.session.execute(permissions_query).fetchall()
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
    # actions do not have permissions for anonymous users at this time
    if user_id is None:
        return []
    if permissions == Permissions.NONE:
        return []

    permissions_query = get_permissions_query(
        action_ids=None,
        user_id=user_id,
    )
    permissions_subquery = permissions_query.having(
        permissions_query.selected_columns.permissions >= permissions
    ).subquery()
    actions_query = models.Action.query.filter(
        models.Action.id.in_(db.select(permissions_subquery.c.action_id))
    )
    if action_type_id is not None:
        actions_query = actions_query.filter_by(action_type_id=action_type_id)
    return [
        Action.from_database(action)
        for action in actions_query.all()
    ]


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
    permissions_query = get_permissions_query(
        action_ids=None,
        user_id=user_id,
    )
    permissions_subquery = permissions_query.having(
        permissions_query.selected_columns.permissions >= Permissions.READ
    ).subquery()
    actions_query = models.Action.query.filter(
        models.Action.id.in_(db.select(permissions_subquery.c.action_id))
    )

    if owner_id is not None:
        actions_query = actions_query.filter_by(
            user_id=owner_id
        )
    if not include_hidden_actions:
        user = users.get_user(user_id)
        if not user.is_admin:
            actions_query = actions_query.filter_by(
                is_hidden=False
            )

    if action_type_id is not None:
        actions_query = actions_query.filter_by(type_id=action_type_id)
    visible_actions = [
        Action.from_database(action)
        for action in actions_query.all()
    ]
    return actions.sort_actions_for_user(actions=visible_actions, user_id=user_id)
