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
from .. import db
from .instruments import get_action
from .groups import get_user_groups, get_group_member_ids
from ..models import Permissions, UserObjectPermissions, GroupObjectPermissions, PublicObjects, Objects, ActionType, Action, Object, DefaultUserPermissions, DefaultGroupPermissions, DefaultPublicPermissions


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def object_is_public(object_id):
    return PublicObjects.query.filter_by(object_id=object_id).first() is not None


def set_object_public(object_id, is_public=True):
    if not is_public:
        PublicObjects.query.filter_by(object_id=object_id).delete()
    elif not object_is_public(object_id):
        db.session.add(PublicObjects(object_id=object_id))
    db.session.commit()


def get_object_permissions_for_users(object_id, include_instrument_responsible_users=True, include_groups=True):
    object_permissions = {}
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
    return object_permissions


def get_object_permissions_for_groups(object_id: int) -> typing.Dict[int, Permissions]:
    object_permissions = {}
    for group_object_permissions in GroupObjectPermissions.query.filter_by(object_id=object_id).all():
        if group_object_permissions.permissions != Permissions.NONE:
            object_permissions[group_object_permissions.group_id] = group_object_permissions.permissions
    return object_permissions


def _get_object_responsible_user_ids(object_id):
    object = Objects.get_current_object(object_id, connection=db.engine)
    action = get_action(object.action_id)
    if action is None or action.instrument is None:
        return []
    return [user.id for user in action.instrument.responsible_users]


def get_user_object_permissions(object_id, user_id, include_instrument_responsible_users=True, include_groups=True):
    assert user_id is not None

    if include_instrument_responsible_users:
        # instrument responsible users always have GRANT permissions for an object
        if user_id in _get_object_responsible_user_ids(object_id):
            return Permissions.GRANT
    # other users might have been granted permissions, either individually or as group members
    user_object_permissions = UserObjectPermissions.query.filter_by(object_id=object_id, user_id=user_id).first()
    if user_object_permissions is None:
        permissions = Permissions.NONE
    else:
        permissions = user_object_permissions.permissions
    if include_groups:
        for group in get_user_groups(user_id):
            group_object_permissions = GroupObjectPermissions.query.filter_by(object_id=object_id, group_id=group.id).first()
            if group_object_permissions is not None and permissions in group_object_permissions.permissions:
                permissions = group_object_permissions.permissions
    if Permissions.READ in permissions:
        return permissions
    # lastly, the object may be public, so all users have READ permissions
    if object_is_public(object_id):
        return Permissions.READ
    # otherwise the user has no permissions for this object
    return Permissions.NONE


def set_user_object_permissions(object_id, user_id, permissions: Permissions):
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


def set_initial_permissions(obj):
    default_user_permissions = get_default_permissions_for_users(creator_id=obj.user_id)
    for user_id, permissions in default_user_permissions.items():
        set_user_object_permissions(object_id=obj.object_id, user_id=user_id, permissions=permissions)
    default_group_permissions = get_default_permissions_for_groups(creator_id=obj.user_id)
    for group_id, permissions in default_group_permissions.items():
        set_group_object_permissions(object_id=obj.object_id, group_id=group_id, permissions=permissions)
    should_be_public = default_is_public(creator_id=obj.user_id)
    set_object_public(object_id=obj.object_id, is_public=should_be_public)

Objects.create_object_callbacks.append(set_initial_permissions)


def get_objects_with_permissions(user_id: int, permissions: Permissions, filter_func: typing.Callable=lambda data: True, action_id: int=None, action_type: ActionType=None) -> typing.List[Object]:
    action_table = Action.__table__
    if action_type is not None and action_id is not None:
        action_filter = db.and_(Action.type == action_type, Action.id == action_id)
    elif action_type is not None:
        action_filter = (Action.type == action_type)
    elif action_id is not None:
        action_filter = (Action.id == action_id)
    else:
        action_table = None
        action_filter = None

    objects = Objects.get_current_objects(filter_func=filter_func, action_table=action_table, action_filter=action_filter)
    objects = [obj for obj in objects if permissions in get_user_object_permissions(user_id=user_id, object_id=obj.object_id)]
    return objects


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


def default_is_public(creator_id: int) -> bool:
    public_permissions = DefaultPublicPermissions.query.filter_by(creator_id=creator_id).first()
    if public_permissions is None:
        return False
    return public_permissions.is_public


def set_default_public(creator_id: int, is_public: bool=True) -> None:
    public_permissions = DefaultPublicPermissions.query.filter_by(creator_id=creator_id).first()
    if public_permissions is None:
        public_permissions = DefaultPublicPermissions(creator_id=creator_id, is_public=is_public)
    else:
        public_permissions.is_public = is_public
    db.session.add(public_permissions)
    db.session.commit()
