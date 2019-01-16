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
    user = User(name=name, email=email, type=type)
    db.session.add(user)
    db.session.commit()
    return user
