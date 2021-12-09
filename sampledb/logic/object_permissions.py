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
from .groups import get_user_groups, get_group_member_ids
from .instruments import get_instrument
from .notifications import create_notification_for_having_received_an_objects_permissions_request
from . import objects
from ..models import Permissions, UserObjectPermissions, GroupObjectPermissions, ProjectObjectPermissions, PublicObjects, Action, Object, DefaultUserPermissions, DefaultGroupPermissions, DefaultProjectPermissions, DefaultPublicPermissions
from . import projects
from . import settings
from .users import get_user, get_administrators


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def object_is_public(object_id: int):
    return PublicObjects.query.filter_by(object_id=object_id).first() is not None


def set_object_public(object_id: int, is_public: bool = True):
    if not is_public:
        PublicObjects.query.filter_by(object_id=object_id).delete()
    elif not object_is_public(object_id):
        db.session.add(PublicObjects(object_id=object_id))
    db.session.commit()


def get_object_permissions_for_users(object_id: int, include_instrument_responsible_users: bool = True, include_groups: bool = True, include_projects: bool = True, include_readonly: bool = True, include_admin_permissions: bool = True):
    object_permissions = {}

    if include_admin_permissions:
        for user in get_administrators():
            if not settings.get_user_settings(user.id)['USE_ADMIN_PERMISSIONS']:
                # skip admins who do not use admin permissions
                continue
            if user.is_readonly:
                object_permissions[user.id] = Permissions.READ
            else:
                object_permissions[user.id] = Permissions.GRANT

    for user_object_permissions in UserObjectPermissions.query.filter_by(object_id=object_id).all():
        object_permissions[user_object_permissions.user_id] = user_object_permissions.permissions
    if include_instrument_responsible_users:
        for user_id in _get_object_responsible_user_ids(object_id):
            object_permissions[user_id] = Permissions.GRANT
    if include_groups:
        for group_object_permissions in GroupObjectPermissions.query.filter_by(object_id=object_id).all():
            for user_id in get_group_member_ids(group_object_permissions.group_id):
                if user_id not in object_permissions or object_permissions[user_id] in group_object_permissions.permissions:
                    object_permissions[user_id] = group_object_permissions.permissions
    if include_projects:
        for project_object_permissions in ProjectObjectPermissions.query.filter_by(object_id=object_id).all():
            for user_id, permissions in projects.get_project_member_user_ids_and_permissions(project_object_permissions.project_id, include_groups=include_groups).items():
                permissions = min(permissions, project_object_permissions.permissions)
                previous_permissions = object_permissions.get(user_id, Permissions.NONE)
                object_permissions[user_id] = max(previous_permissions, permissions)
    if include_readonly:
        for user_id in object_permissions:
            if get_user(user_id).is_readonly:
                object_permissions[user_id] = min(object_permissions[user_id], Permissions.READ)
    return object_permissions


def get_object_permissions_for_groups(object_id: int, include_projects: bool = False) -> typing.Dict[int, Permissions]:
    object_permissions = {}
    for group_object_permissions in GroupObjectPermissions.query.filter_by(object_id=object_id).all():
        if group_object_permissions.permissions != Permissions.NONE:
            object_permissions[group_object_permissions.group_id] = group_object_permissions.permissions
    if include_projects:
        for project_object_permissions in ProjectObjectPermissions.query.filter_by(object_id=object_id).all():
            for group_id, permissions in projects.get_project_member_group_ids_and_permissions(project_object_permissions.project_id).items():
                permissions = min(permissions, project_object_permissions.permissions)
                previous_permissions = object_permissions.get(group_id, Permissions.NONE)
                object_permissions[group_id] = max(previous_permissions, permissions)
    return object_permissions


def get_object_permissions_for_projects(object_id: int) -> typing.Dict[int, Permissions]:
    object_permissions = {}
    for project_object_permissions in ProjectObjectPermissions.query.filter_by(object_id=object_id).all():
        if project_object_permissions.permissions != Permissions.NONE:
            object_permissions[project_object_permissions.project_id] = project_object_permissions.permissions
    return object_permissions


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

    if include_instrument_responsible_users:
        # instrument responsible users always have GRANT permissions for an object
        if user_id in _get_object_responsible_user_ids(object_id):
            if include_readonly and user.is_readonly:
                return Permissions.READ
            return Permissions.GRANT
    # other users might have been granted permissions, either individually or as group or project members
    user_object_permissions = UserObjectPermissions.query.filter_by(object_id=object_id, user_id=user_id).first()
    if user_object_permissions is None:
        permissions = Permissions.NONE
    else:
        permissions = user_object_permissions.permissions
    if include_readonly and user.is_readonly and Permissions.READ in permissions:
        return Permissions.READ
    if Permissions.GRANT in permissions:
        return permissions
    if include_groups:
        for group in get_user_groups(user_id):
            group_object_permissions = GroupObjectPermissions.query.filter_by(object_id=object_id, group_id=group.id).first()
            if group_object_permissions is not None and permissions in group_object_permissions.permissions:
                permissions = group_object_permissions.permissions
    if include_readonly and user.is_readonly and Permissions.READ in permissions:
        return Permissions.READ
    if Permissions.GRANT in permissions:
        return permissions
    if include_projects:
        for user_project in projects.get_user_projects(user_id, include_groups=include_groups):
            user_project_permissions = projects.get_user_project_permissions(user_project.id, user_id, include_groups=include_groups)
            if user_project_permissions not in permissions:
                project_object_permissions = ProjectObjectPermissions.query.filter_by(object_id=object_id, project_id=user_project.id).first()
                if project_object_permissions is not None:
                    permissions = min(user_project_permissions, project_object_permissions.permissions)
    if include_readonly and user.is_readonly and Permissions.READ in permissions:
        return Permissions.READ
    if Permissions.READ in permissions:
        return permissions
    # lastly, the object may be public, so all users have READ permissions
    if object_is_public(object_id):
        return Permissions.READ
    # otherwise the user has no permissions for this object
    return Permissions.NONE


def set_user_object_permissions(object_id: int, user_id: int, permissions: Permissions):
    assert user_id is not None
    if permissions == Permissions.NONE:
        UserObjectPermissions.query.filter_by(object_id=object_id, user_id=user_id).delete()
    else:
        user_object_permissions = UserObjectPermissions.query.filter_by(object_id=object_id, user_id=user_id).first()
        if user_object_permissions is None:
            user_object_permissions = UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=permissions)
        else:
            user_object_permissions.permissions = permissions
        db.session.add(user_object_permissions)
    db.session.commit()


def set_group_object_permissions(object_id: int, group_id: int, permissions: Permissions):
    assert group_id is not None
    if permissions == Permissions.NONE:
        GroupObjectPermissions.query.filter_by(object_id=object_id, group_id=group_id).delete()
    else:
        group_object_permissions = GroupObjectPermissions.query.filter_by(object_id=object_id, group_id=group_id).first()
        if group_object_permissions is None:
            group_object_permissions = GroupObjectPermissions(object_id=object_id, group_id=group_id, permissions=permissions)
        else:
            group_object_permissions.permissions = permissions
        db.session.add(group_object_permissions)
    db.session.commit()


def set_project_object_permissions(object_id: int, project_id: int, permissions: Permissions) -> None:
    """
    Sets the permissions for a project for an object. Clears the permissions
    if called with Permissions.NONE.

    :param object_id: the object ID of an existing object
    :param project_id: the project ID of an existing probject
    :param permissions: the new permissions
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    """
    projects.get_project(project_id)
    if permissions == Permissions.NONE:
        ProjectObjectPermissions.query.filter_by(object_id=object_id, project_id=project_id).delete()
    else:
        project_object_permissions = ProjectObjectPermissions.query.filter_by(object_id=object_id, project_id=project_id).first()
        if project_object_permissions is None:
            project_object_permissions = ProjectObjectPermissions(project_id=project_id, object_id=object_id, permissions=permissions)
        else:
            project_object_permissions.permissions = permissions
        db.session.add(project_object_permissions)
    db.session.commit()


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
        limit: typing.Optional[int] = None,
        offset: typing.Optional[int] = None,
        action_id: typing.Optional[int] = None,
        action_type_id: typing.Optional[int] = None,
        object_ids: typing.Optional[typing.Sequence[int]] = None
) -> typing.List[Object]:

    user = get_user(user_id)

    # readonly users may not have more than READ permissions
    if user.is_readonly and permissions != Permissions.READ:
        return []

    if action_type_id is not None and action_id is not None:
        action_filter = db.and_(Action.type_id == action_type_id, Action.id == action_id)
    elif action_type_id is not None:
        action_filter = (Action.type_id == action_type_id)
    elif action_id is not None:
        action_filter = (Action.id == action_id)
    else:
        action_filter = None

    if user.is_admin and settings.get_user_settings(user.id)['USE_ADMIN_PERMISSIONS']:
        # admins who use admin permissions do not need permission-based filtering
        stmt = db.text("""
        SELECT
        o.object_id, o.data -> 'name' -> 'text' as name_json, o.action_id, 3 as max_permission, o.data -> 'tags' as tags
        FROM objects_current AS o
        """)
    else:
        stmt = db.text("""
        SELECT
        o.object_id, o.data -> 'name' -> 'text' as name_json, o.action_id, p.max_permission, o.data -> 'tags' as tags
        FROM (
            SELECT
            object_id, MAX(permissions_int) AS max_permission
            FROM user_object_permissions_by_all
            WHERE user_id = :user_id OR user_id IS NULL
            GROUP BY (object_id)
            HAVING MAX(permissions_int) >= :min_permissions_int
        ) AS p
        JOIN objects_current AS o ON o.object_id = p.object_id
        """)

    stmt = stmt.columns(
        objects.Objects._current_table.c.object_id,
        sqlalchemy.sql.expression.column('name_json'),
        objects.Objects._current_table.c.action_id,
        sqlalchemy.sql.expression.column('max_permission'),
        sqlalchemy.sql.expression.column('tags')
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
        action_filter = (Action.type_id == action_type_id)
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
        o.object_id, o.version_id, o.action_id, jsonb_set('{"name": {"_type": "text", "text": ""}}', '{name,text}', o.data -> 'name' -> 'text') as data, '{"title": "Object", "type": "object", "properties": {"name": {"title": "Name", "type": "text"}}}'::jsonb as schema, o.user_id, o.utc_datetime
        FROM objects_current AS o
        """
    else:
        stmt = """
        SELECT
        o.object_id, o.version_id, o.action_id, o.data, o.schema, o.user_id, o.utc_datetime
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
        objects.Objects._current_table.c.utc_datetime
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


class InvalidDefaultPermissionsError(Exception):
    pass


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
    public_permissions = DefaultPublicPermissions.query.filter_by(creator_id=creator_id).first()
    if public_permissions is None:
        return False
    return public_permissions.is_public


def set_default_public(creator_id: int, is_public: bool = True) -> None:
    public_permissions = DefaultPublicPermissions.query.filter_by(creator_id=creator_id).first()
    if public_permissions is None:
        public_permissions = DefaultPublicPermissions(creator_id=creator_id, is_public=is_public)
    else:
        public_permissions.is_public = is_public
    db.session.add(public_permissions)
    db.session.commit()


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
    PublicObjects.query.filter_by(object_id=target_object_id).delete()
    UserObjectPermissions.query.filter_by(object_id=target_object_id).delete()
    GroupObjectPermissions.query.filter_by(object_id=target_object_id).delete()
    ProjectObjectPermissions.query.filter_by(object_id=target_object_id).delete()

    if PublicObjects.query.filter_by(object_id=source_object_id).first() is not None:
        db.session.add(PublicObjects(object_id=target_object_id))
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
