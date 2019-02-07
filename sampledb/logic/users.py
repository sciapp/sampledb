# coding: utf-8
"""

"""

import typing

from .. import db
from . import errors
from .. models import User, UserType


def get_user(user_id: int) -> User:
    user = User.query.get(user_id)
    if user is None:
        raise errors.UserDoesNotExistError()
    return user


def get_users() -> typing.List[User]:
    """
    Returns all users.

    :return: the list of users
    """
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
