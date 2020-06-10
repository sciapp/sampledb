# coding: utf-8
"""

"""

import typing

from .. import db
from . import errors
from .. models import User, UserType


def get_user(user_id: int) -> User:
    if user_id is None:
        raise TypeError("user_id must be int")
    user = User.query.get(user_id)
    if user is None:
        raise errors.UserDoesNotExistError()
    return user


def get_users(exclude_hidden: bool = False) -> typing.List[User]:
    """
    Returns all users.

    :param exclude_hidden: whether or not to exclude hidden users
    :return: the list of users
    """
    if exclude_hidden:
        return User.query.filter_by(is_hidden=False).all()
    return User.query.all()


def get_users_by_name(name: str) -> typing.List[User]:
    """
    Return all users with a given name.

    :param name: the user name to search for
    :return: the list of users with this name
    """
    return User.query.filter_by(name=name).all()


def create_user(name: str, email: str, type: UserType) -> User:
    """
    Create a new user.

    This function cannot create a user as an administrator. To set whether or
    not a user is an administrator, use the set_administrator script or modify
    the User object returned by this function.

    :param name: the user's name
    :param email: the user's email address
    :param type: the user's type
    :return: the newly created user
    """
    user = User(name=name, email=email, type=type)
    db.session.add(user)
    db.session.commit()
    return user


def set_user_readonly(user_id: int, readonly: bool) -> None:
    """
    Set whether a user should be limited to READ permissions.

    :param user_id: the user ID of an existing user
    :param readonly: True, if the user should be read only, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """

    user = get_user(user_id)
    user.is_readonly = readonly
    db.session.add(user)
    db.session.commit()


def set_user_hidden(user_id: int, hidden: bool) -> None:
    """
    Set whether a user should be hidden from user lists.

    :param user_id: the user ID of an existing user
    :param hidden: True, if the user should be hidden, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """

    user = get_user(user_id)
    user.is_hidden = hidden
    db.session.add(user)
    db.session.commit()


def set_user_administrator(user_id: int, is_admin: bool) -> None:
    """
    Set whether a user is an administrator.

    :param user_id: the user ID of an existing user
    :param is_admin: True, if the user is an administrator, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """

    user = get_user(user_id)
    user.is_admin = is_admin
    db.session.add(user)
    db.session.commit()
