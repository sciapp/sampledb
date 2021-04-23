# coding: utf-8
"""

"""

import collections
import datetime
import typing

import flask

from .. import db
from . import errors
from .. models import users, User, UserType


class UserInvitation(collections.namedtuple('UserInvitation', ['id', 'inviter_id', 'utc_datetime', 'accepted'])):
    """
    This class provides an immutable wrapper around models.users.UserInvitation.
    """

    def __new__(cls, id: int, inviter_id: int, utc_datetime: datetime.datetime, accepted: bool):
        self = super(UserInvitation, cls).__new__(cls, id, inviter_id, utc_datetime, accepted)
        return self

    @classmethod
    def from_database(cls, user_invitation: users.UserInvitation) -> 'UserInvitation':
        return UserInvitation(
            id=user_invitation.id,
            inviter_id=user_invitation.inviter_id,
            utc_datetime=user_invitation.utc_datetime,
            accepted=user_invitation.accepted
        )

    @property
    def expired(self):
        expiration_datetime = self.utc_datetime + datetime.timedelta(seconds=flask.current_app.config['INVITATION_TIME_LIMIT'])
        return datetime.datetime.utcnow() >= expiration_datetime


def get_user(user_id: int) -> User:
    if user_id is None:
        raise TypeError("user_id must be int")
    user = User.query.get(user_id)
    if user is None:
        raise errors.UserDoesNotExistError()
    return user


def get_users(exclude_hidden: bool = False, order_by: typing.Optional[db.Column] = User.name) -> typing.List[User]:
    """
    Returns all users.

    :param exclude_hidden: whether or not to exclude hidden users
    :param order_by: Column to order the users by, or None
    :return: the list of users
    """
    user_query = User.query
    if exclude_hidden:
        user_query = user_query.filter_by(is_hidden=False)
    if order_by is not None:
        user_query = user_query.order_by(order_by)
    return user_query.all()


def get_administrators() -> typing.List[User]:
    """
    Returns all current administrators.

    :return: the list of administrators
    """
    return User.query.filter_by(is_admin=True).all()


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


def set_user_active(user_id: int, active: bool) -> None:
    """
    Set whether a user should be allowed to sign in.

    :param user_id: the user ID of an existing user
    :param active: True, if the user should be active, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """

    user = get_user(user_id)
    user.is_active = active
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


def get_user_invitation(invitation_id: int) -> UserInvitation:
    """
    Get an existing invitation.

    :param invitation_id: the ID of an existing invitation
    :return: the invitation
    :raise errors.UserInvitationDoesNotExistError: when no invitation with
        the given ID exists
    """
    invitation = users.UserInvitation.query.filter_by(id=invitation_id).first()
    if invitation is None:
        raise errors.UserInvitationDoesNotExistError()
    return UserInvitation.from_database(invitation)


def set_user_invitation_accepted(invitation_id: int) -> None:
    """
    Mark an invitation as having been accepted.

    :param invitation_id: the ID of an existing invitation
    :raise errors.UserInvitationDoesNotExistError: when no invitation with
        the given ID exists
    """
    invitation = users.UserInvitation.query.filter_by(id=invitation_id).first()
    if invitation is None:
        raise errors.UserInvitationDoesNotExistError()
    invitation.accepted = True
    db.session.add(invitation)
    db.session.commit()
