# coding: utf-8
"""

"""

from sqlalchemy.exc import IntegrityError
import collections
import typing
from .. import db
from ..models import groups, User


class Group(collections.namedtuple('Group', ['id', 'name', 'description'])):
    def __new__(cls, id: int, name: str, description: str):
        self = super(Group, cls).__new__(cls, id, name, description)
        return self

    @classmethod
    def from_database(cls, group: groups.Group) -> 'Group':
        return Group(id=group.id, name=group.name, description=group.description)


class GroupDoesNotExistError(ValueError):
    pass


class GroupAlreadyExistsError(ValueError):
    pass


class UserDoesNotExistError(ValueError):
    pass


class UserNotMemberOfGroupError(ValueError):
    pass


class UserAlreadyMemberOfGroupError(ValueError):
    pass


class InvalidGroupNameError(ValueError):
    pass


def create_group(name: str, description: str, initial_user_id: int) -> int:
    if not 1 <= len(name) <= 100:
        raise InvalidGroupNameError()
    user = User.query.get(initial_user_id)
    if user is None:
        raise UserDoesNotExistError()
    group = groups.Group(name=name, description=description)
    group.members.append(user)
    db.session.add(group)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing_group = groups.Group.query.filter_by(name=name).first()
        if existing_group is not None:
            raise GroupAlreadyExistsError()
        raise
    return group.id


def update_group(group_id: int, name: str, description: str='') -> None:
    if not 1 <= len(name) <= 100:
        raise InvalidGroupNameError()
    group = groups.Group.query.get(group_id)
    if group is None:
        raise GroupDoesNotExistError()
    group.name = name
    group.description = description
    db.session.add(group)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing_group = groups.Group.query.filter_by(name=name).first()
        if existing_group is not None:
            raise GroupAlreadyExistsError()
        raise


def delete_group(group_id: int) -> None:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise GroupDoesNotExistError()
    db.session.delete(group)
    db.session.commit()


def get_group(group_id: int) -> Group:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise GroupDoesNotExistError()
    return Group.from_database(group)


def get_groups() -> typing.List[Group]:
    return [Group.from_database(group) for group in groups.Group.query.all()]


def get_group_member_ids(group_id: int) -> typing.List[int]:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise GroupDoesNotExistError()
    return [user.id for user in group.members]


def get_user_groups(user_id: int) -> typing.List[Group]:
    user = User.query.get(user_id)
    if user is None:
        raise UserDoesNotExistError()
    return [Group.from_database(group) for group in user.groups]


def add_user_to_group(group_id: int, user_id: int) -> None:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise GroupDoesNotExistError()
    user = User.query.get(user_id)
    if user is None:
        raise UserDoesNotExistError()
    if user in group.members:
        raise UserAlreadyMemberOfGroupError()
    group.members.append(user)
    db.session.commit()


def remove_user_from_group(group_id: int, user_id: int) -> None:
    group = groups.Group.query.get(group_id)
    if group is None:
        raise GroupDoesNotExistError()
    user = User.query.get(user_id)
    if user is None:
        raise UserDoesNotExistError()
    if user not in group.members:
        raise UserNotMemberOfGroupError()
    group.members.remove(user)
    if not group.members:
        db.session.delete(group)
    db.session.commit()
