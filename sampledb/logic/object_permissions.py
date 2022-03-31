# coding: utf-8
"""
Object Permissions

There are three types of permissions for each object:
 - READ, being able to access all information on an object,
 - WRITE, being able to update an object, and
 - GRANT, being able to grant permissions to other users.

When an object is created, its creator initially gets GRANT permissions for the object. In addition, if the object
was created performing an instrument action, the instrument responsible users will have GRANT access rights, not as
individuals, but in their role of responsible users. So even when a user becomes responsible user AFTER an object was
created using an instrument, this user will then have GRANT rights, until he is removed from the list of responsible
users for the instrument.

Objects can be made public, which grants READ permissions to any logged-in user trying to access the object.
"""

import typing

import sqlalchemy

from .. import db
from . import errors
from . import actions
from .default_permissions import get_default_permissions_for_users, get_default_permissions_for_groups, get_default_permissions_for_projects, default_is_public
from .instruments import get_instrument
from .notifications import create_notification_for_having_received_an_objects_permissions_request
from . import objects
from ..models import Permissions, UserObjectPermissions, GroupObjectPermissions, ProjectObjectPermissions, AllUserObjectPermissions, Action, Object
from . import settings
from .users import get_user
from .permissions import ResourcePermissions


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


object_permissions = ResourcePermissions(
    resource_id_name='object_id',
    all_user_permissions_table=AllUserObjectPermissions,
    user_permissions_table=UserObjectPermissions,
    group_permissions_table=GroupObjectPermissions,
    project_permissions_table=ProjectObjectPermissions,
    check_resource_exists=lambda resource_id: objects.check_object_exists(object_id=resource_id)
)


def get_object_permissions_for_all_users(object_id: int) -> Permissions:
    return object_permissions.get_permission_for_all_users(resource_id=object_id)


def set_object_permissions_for_all_users(object_id: int, permissions: Permissions) -> None:
    object_permissions.set_permissions_for_all_users(resource_id=object_id, permissions=permissions)


def get_object_permissions_for_users(
        object_id: int,
        include_instrument_responsible_users: bool = True,
        include_groups: bool = True,
        include_projects: bool = True,
        include_readonly: bool = True,
        include_admin_permissions: bool = True
):
    additional_permissions = {}
    if include_instrument_responsible_users:
        for user_id in _get_object_responsible_user_ids(object_id):
            additional_permissions[user_id] = Permissions.GRANT
    return object_permissions.get_permissions_for_users(
        resource_id=object_id,
        include_groups=include_groups,
        include_projects=include_projects,
        include_admin_permissions=include_admin_permissions,
        limit_readonly_users=include_readonly,
        additional_permissions=additional_permissions
    )


def set_user_object_permissions(object_id: int, user_id: int, permissions: Permissions):
    object_permissions.set_permissions_for_user(resource_id=object_id, user_id=user_id, permissions=permissions)


def get_object_permissions_for_groups(object_id: int, include_projects: bool = False) -> typing.Dict[int, Permissions]:
    return object_permissions.get_permissions_for_groups(resource_id=object_id, include_projects=include_projects)


def set_group_object_permissions(object_id: int, group_id: int, permissions: Permissions):
    object_permissions.set_permissions_for_group(resource_id=object_id, group_id=group_id, permissions=permissions)


def get_object_permissions_for_projects(object_id: int) -> typing.Dict[int, Permissions]:
    return object_permissions.get_permissions_for_projects(resource_id=object_id)


def set_project_object_permissions(object_id: int, project_id: int, permissions: Permissions) -> None:
    object_permissions.set_permissions_for_project(resource_id=object_id, project_id=project_id, permissions=permissions)


def object_is_public(object_id: int):
    return Permissions.READ in get_object_permissions_for_all_users(object_id=object_id)


def set_object_public(object_id: int, is_public: bool = True):
    set_object_permissions_for_all_users(object_id, Permissions.READ if is_public else Permissions.NONE)


def _get_object_responsible_user_ids(object_id):
    object = objects.get_object(object_id)
    try:
        action = actions.get_action(object.action_id)
    except errors.ActionDoesNotExistError:
        return []
    if action.instrument_id is None:
        return []
    instrument = get_instrument(action.instrument_id)
    return [user.id for user in instrument.responsible_users]


def get_user_object_permissions(object_id: int, user_id: int, include_instrument_responsible_users: bool = True, include_groups: bool = True, include_projects: bool = True, include_readonly: bool = True, include_admin_permissions: bool = True):
    user = get_user(user_id)

    if include_admin_permissions:
        # administrators have GRANT permissions if they use admin permissions
        if user.is_admin and settings.get_user_settings(user.id)['USE_ADMIN_PERMISSIONS']:
            # unless they are limited to READ permissions
            if user.is_readonly:
                return Permissions.READ
            else:
                return Permissions.GRANT

    # select permissions from view for efficiency
    if include_instrument_responsible_users and include_groups and include_projects:
        stmt = db.text("""
        SELECT
        MAX(permissions_int)
        FROM user_object_permissions_by_all
        WHERE (user_id = :user_id OR user_id IS NULL) AND object_id = :object_id
        """)
        permissions_int = db.engine.execute(stmt, {
            'user_id': user_id,
            'object_id': object_id
        }).fetchone()[0]
        if permissions_int is None or permissions_int <= 0:
            return Permissions.NONE
        elif include_readonly and user.is_readonly and permissions_int in (1, 2, 3):
            return Permissions.READ
        elif permissions_int == 1:
            return Permissions.READ
        elif permissions_int == 2:
            return Permissions.WRITE
        elif permissions_int >= 3:
            return Permissions.GRANT

    additional_permissions = Permissions.NONE
    if include_instrument_responsible_users:
        # instrument responsible users have GRANT permissions for an object created with instrument
        if user_id in _get_object_responsible_user_ids(object_id):
            additional_permissions = max(additional_permissions, Permissions.GRANT)

    return object_permissions.get_permissions_for_user(
        resource_id=object_id,
        user_id=user_id,
        include_all_users=True,
        include_groups=include_groups,
        include_projects=include_projects,
        # admin permissions have already been checked above
        include_admin_permissions=False,
        limit_readonly_users=include_readonly,
        additional_permissions=additional_permissions
    )


def set_initial_permissions(obj):
    default_user_permissions = get_default_permissions_for_users(creator_id=obj.user_id)
    for user_id, permissions in default_user_permissions.items():
        set_user_object_permissions(object_id=obj.object_id, user_id=user_id, permissions=permissions)
    default_group_permissions = get_default_permissions_for_groups(creator_id=obj.user_id)
    for group_id, permissions in default_group_permissions.items():
        set_group_object_permissions(object_id=obj.object_id, group_id=group_id, permissions=permissions)
    default_project_permissions = get_default_permissions_for_projects(creator_id=obj.user_id)
    for project_id, permissions in default_project_permissions.items():
        set_project_object_permissions(object_id=obj.object_id, project_id=project_id, permissions=permissions)
    should_be_public = default_is_public(creator_id=obj.user_id)
    set_object_public(object_id=obj.object_id, is_public=should_be_public)


def get_object_info_with_permissions(
        user_id: int,
        permissions: Permissions,
        *,
        limit: typing.Optional[int] = None,
        offset: typing.Optional[int] = None,
        action_id: typing.Optional[int] = None,
        action_ids: typing.Optional[typing.Sequence[int]] = None,
        action_type_id: typing.Optional[int] = None,
        object_ids: typing.Optional[typing.Sequence[int]] = None
) -> typing.List[Object]:

    user = get_user(user_id)

    # readonly users may not have more than READ permissions
    if user.is_readonly and permissions != Permissions.READ:
        return []

    action_filters = []
    if action_type_id is not None:
        action_filters.append(Action.type_id == action_type_id)
    if action_id is not None:
        action_filters.append(Action.id == action_id)
    if action_ids is not None:
        action_filters.append(Action.id.in_(tuple(action_ids)))
    if action_filters:
        action_filter = action_filters.pop(0)
        for additional_action_filter in action_filters:
            action_filter = db.and_(action_filter, additional_action_filter)
    else:
        action_filter = None

    if user.is_admin and settings.get_user_settings(user.id)['USE_ADMIN_PERMISSIONS']:
        # admins who use admin permissions do not need permission-based filtering
        stmt = db.text("""
        SELECT
            o.object_id, o.name_cache AS name_json, o.action_id, 3 AS max_permission, o.tags_cache as tags, o.fed_object_id, COALESCE(c.name, c.address, c.uuid) AS component_name
        FROM objects_current AS o
        LEFT JOIN components AS c ON c.id = o.component_id
        """)
    else:
        stmt = db.text("""
        SELECT
            o.object_id, o.name_cache AS name_json, o.action_id, p.max_permission, o.tags_cache as tags, o.fed_object_id, COALESCE(c.name, c.address, c.uuid) AS component_name
        FROM (
            SELECT
            object_id, MAX(permissions_int) AS max_permission
            FROM user_object_permissions_by_all
            WHERE user_id = :user_id OR user_id IS NULL
            GROUP BY (object_id)
            HAVING MAX(permissions_int) >= :min_permissions_int
        ) AS p
        JOIN objects_current AS o ON o.object_id = p.object_id
        LEFT JOIN components AS c ON c.id = o.component_id
        """)

    stmt = stmt.columns(
        objects.Objects._current_table.c.object_id,
        sqlalchemy.sql.expression.column('name_json'),
        objects.Objects._current_table.c.action_id,
        sqlalchemy.sql.expression.column('max_permission'),
        sqlalchemy.sql.expression.column('tags'),
        sqlalchemy.sql.expression.column('fed_object_id'),
        sqlalchemy.sql.expression.column('component_name')
    )

    parameters = {
        'min_permissions_int': permissions.value,
        'user_id': user_id
    }

    table = stmt.alias('tbl')

    where = table.c.action_id.in_(db.select([Action.__table__.c.id], whereclause=action_filter)) if action_filter is not None else None

    if object_ids is not None:
        object_id_where = table.c.object_id.in_(tuple(object_ids))
        if where is None:
            where = object_id_where
        else:
            where = db.and_(where, object_id_where)

    table = db.select(
        columns=[table],
        whereclause=where
    ).order_by(db.desc(table.c.object_id)).limit(limit).offset(offset)

    object_infos = db.session.execute(table, parameters).fetchall()

    return object_infos


def get_objects_with_permissions(
        user_id: int,
        permissions: Permissions,
        filter_func: typing.Callable = lambda data: True,
        sorting_func: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
        limit: typing.Optional[int] = None,
        offset: typing.Optional[int] = None,
        action_id: typing.Optional[int] = None,
        action_type_id: typing.Optional[int] = None,
        other_user_id: typing.Optional[int] = None,
        other_user_permissions: typing.Optional[Permissions] = None,
        group_id: typing.Optional[int] = None,
        group_permissions: typing.Optional[Permissions] = None,
        project_id: typing.Optional[int] = None,
        project_permissions: typing.Optional[Permissions] = None,
        object_ids: typing.Optional[typing.Sequence[int]] = None,
        num_objects_found: typing.Optional[typing.List[int]] = None,
        name_only: bool = False,
        **kwargs
) -> typing.List[Object]:

    user = get_user(user_id)

    # readonly users may not have more than READ permissions
    if user.is_readonly and permissions != Permissions.READ:
        return []

    if action_type_id is not None and action_id is not None:
        action_filter = db.and_(Action.type_id == action_type_id, Action.id == action_id)
    elif action_type_id is not None:
        if action_type_id <= 0:
            # merge with default types of other databases
            action_filter = (db.or_(Action.type_id == action_type_id, Action.type.has(fed_id=action_type_id)))
        else:
            action_filter = (Action.type_id == action_type_id)
        # action_filter = (Action.type_id == action_type_id)
    elif action_id is not None:
        action_filter = (Action.id == action_id)
    else:
        action_filter = None

    parameters = {
        'min_permissions_int': permissions.value,
        'user_id': user_id
    }

    if name_only:
        stmt = """
        SELECT
        o.object_id, o.version_id, o.action_id, jsonb_set('{"name": {"_type": "text", "text": ""}}', '{name,text}', o.name_cache::jsonb) as data, '{"title": "Object", "type": "object", "properties": {"name": {"title": "Name", "type": "text"}}}'::jsonb as schema, o.user_id, o.utc_datetime, o.fed_object_id, o.fed_version_id, o.component_id
        FROM objects_current AS o
        """
    else:
        stmt = """
        SELECT
        o.object_id, o.version_id, o.action_id, o.data, o.schema, o.user_id, o.utc_datetime, o.fed_object_id, o.fed_version_id, o.component_id
        FROM objects_current AS o
        """

    if not user.is_admin or not settings.get_user_settings(user.id)['USE_ADMIN_PERMISSIONS']:
        stmt += """
        JOIN (
            SELECT
            u.object_id
            FROM user_object_permissions_by_all as u
            WHERE u.user_id = :user_id OR u.user_id IS NULL
            GROUP BY (u.object_id)
            HAVING MAX(u.permissions_int) >= :min_permissions_int
        ) AS up
        ON o.object_id = up.object_id
        """

    if other_user_id is not None:
        stmt += """
        JOIN (
            SELECT
            u.object_id
            FROM user_object_permissions_by_all as u
            WHERE u.user_id = :other_user_id OR u.user_id IS NULL
            GROUP BY (u.object_id)
            HAVING MAX(u.permissions_int) >= :min_other_user_permissions_int
        ) AS oup
        ON o.object_id = oup.object_id
        """
        parameters['other_user_id'] = other_user_id
        if other_user_permissions is None:
            other_user_permissions = permissions
        parameters['min_other_user_permissions_int'] = other_user_permissions.value

    if project_id is not None:
        stmt += """
        JOIN project_object_permissions as pp
        ON (
            pp.object_id = o.object_id AND
            pp.project_id = :project_id AND
            ('{"READ": 1, "WRITE": 2, "GRANT": 3}'::jsonb ->> pp.permissions::text)::int >= :min_project_permissions_int
        )
        """
        parameters['project_id'] = project_id
        if project_permissions is None:
            project_permissions = permissions
        parameters['min_project_permissions_int'] = project_permissions.value

    if group_id is not None:
        stmt += """
        JOIN group_object_permissions as gp
        ON (
            gp.object_id = o.object_id AND
            gp.group_id = :group_id AND
            ('{"READ": 1, "WRITE": 2, "GRANT": 3}'::jsonb ->> gp.permissions::text)::int >= :min_group_permissions_int
        )
        """
        parameters['group_id'] = group_id
        if group_permissions is None:
            group_permissions = permissions
        parameters['min_group_permissions_int'] = group_permissions.value

    if object_ids:
        stmt += """
        WHERE o.object_id IN :object_ids
        """
        parameters['object_ids'] = tuple(object_ids)

    table = sqlalchemy.sql.alias(db.text(stmt).columns(
        objects.Objects._current_table.c.object_id,
        objects.Objects._current_table.c.version_id,
        objects.Objects._current_table.c.action_id,
        objects.Objects._current_table.c.data,
        objects.Objects._current_table.c.schema,
        objects.Objects._current_table.c.user_id,
        objects.Objects._current_table.c.utc_datetime,
        objects.Objects._current_table.c.fed_object_id,
        objects.Objects._current_table.c.fed_version_id,
        objects.Objects._current_table.c.component_id
    ))

    return objects.get_objects(
        filter_func=filter_func,
        action_filter=action_filter,
        table=table,
        parameters=parameters,
        sorting_func=sorting_func,
        limit=limit,
        offset=offset,
        num_objects_found=num_objects_found,
        **kwargs
    )


def request_object_permissions(requester_id: int, object_id: int) -> None:
    permissions_by_user = get_object_permissions_for_users(object_id)
    if Permissions.READ in permissions_by_user.get(requester_id, Permissions.NONE):
        return
    granting_user_ids = [
        user_id
        for user_id, permissions in permissions_by_user.items()
        if Permissions.GRANT in permissions
    ]
    for user_id in granting_user_ids:
        create_notification_for_having_received_an_objects_permissions_request(user_id, object_id, requester_id)


def copy_permissions(target_object_id: int, source_object_id: int) -> None:
    AllUserObjectPermissions.query.filter_by(object_id=target_object_id).delete()
    UserObjectPermissions.query.filter_by(object_id=target_object_id).delete()
    GroupObjectPermissions.query.filter_by(object_id=target_object_id).delete()
    ProjectObjectPermissions.query.filter_by(object_id=target_object_id).delete()

    all_user_object_permissions = AllUserObjectPermissions.query.filter_by(object_id=source_object_id).first()
    if all_user_object_permissions is not None:
        db.session.add(AllUserObjectPermissions(object_id=target_object_id, permissions=all_user_object_permissions.permissions))
    for user_object_permissions in UserObjectPermissions.query.filter_by(object_id=source_object_id).all():
        db.session.add(UserObjectPermissions(
            object_id=target_object_id,
            user_id=user_object_permissions.user_id,
            permissions=user_object_permissions.permissions
        ))
    for group_object_permissions in GroupObjectPermissions.query.filter_by(object_id=source_object_id).all():
        db.session.add(GroupObjectPermissions(
            object_id=target_object_id,
            group_id=group_object_permissions.group_id,
            permissions=group_object_permissions.permissions
        ))
    for project_object_permissions in ProjectObjectPermissions.query.filter_by(object_id=source_object_id).all():
        db.session.add(ProjectObjectPermissions(
            object_id=target_object_id,
            project_id=project_object_permissions.project_id,
            permissions=project_object_permissions.permissions
        ))
    db.session.commit()
