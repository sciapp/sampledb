# coding: utf-8
"""

"""

from sqlalchemy.exc import IntegrityError
import collections
import typing
from .. import db
from ..models import groups
from .user import get_user
from . import errors


class Group(collections.namedtuple('Group', ['id', 'name', 'description'])):
    def __new__(cls, id: int, name: str, description: str):
        self = super(Group, cls).__new__(cls, id, name, description)
        return self

    @classmethod
    def from_database(cls, group: groups.Group) -> 'Group':
        return Group(id=group.id, name=group.name, description=group.description)


def create_group(name: str, description: str, initial_user_id: int) -> int:
    if not 1 <= len(name) <= 100:
        raise errors.InvalidGroupNameError()
    user = get_user(initial_user_id)
    if user is None:
        raise errors.UserDoesNotExistError()
    group = groups.Group(name=name, description=description)
    group.members.append(user)
    db.session.add(group)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing_group = groups.Group.query.filter_by(name=name).first()
        if existing_group is not None:
            raise errors.GroupAlreadyExistsError()
        raise
    return group.id


def update_group(group_id: int, name: str, description: str='') -> None:
    if not 1 <= len(name) <= 100:
        raise errors.InvalidGroupNameError()
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    group.name = name
    group.description = description
    db.session.add(group)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing_group = groups.Group.query.filter_by(name=name).first()
        if existing_group is not None:
            raise errors.GroupAlreadyExistsError()
        raise


def delete_group(group_id: int) -> None:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    db.session.delete(group)
    db.session.commit()


def get_group(group_id: int) -> Group:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    return Group.from_database(group)


def get_groups() -> typing.List[Group]:
    return [Group.from_database(group) for group in groups.Group.query.all()]


def get_group_member_ids(group_id: int) -> typing.List[int]:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    return [user.id for user in group.members]


def get_user_groups(user_id: int) -> typing.List[Group]:
    user = get_user(user_id)
    if user is None:
        raise errors.UserDoesNotExistError()
    return [Group.from_database(group) for group in user.groups]


def add_user_to_group(group_id: int, user_id: int) -> None:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    user = get_user(user_id)
    if user is None:
        raise errors.UserDoesNotExistError()
    if user in group.members:
        raise errors.UserAlreadyMemberOfGroupError()
    group.members.append(user)
    db.session.commit()


def remove_user_from_group(group_id: int, user_id: int) -> None:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    user = get_user(user_id)
    if user is None:
        raise errors.UserDoesNotExistError()
    if user not in group.members:
        raise errors.UserNotMemberOfGroupError()
    group.members.remove(user)
    if not group.members:
        db.session.delete(group)
    db.session.commit()
