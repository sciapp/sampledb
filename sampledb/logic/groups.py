# coding: utf-8
"""
Logic module for user managed groups

Users can create uniquely named groups and use them to more easily manage
permissions for samples or measurements. At this time, all group members
are equally able to add new members to a group and to modify a group's
name and description.

This module provides a procedural interface to the underlying database model,
with the immutable Group class accessible to the developer instead of an
SQLAlchemy ORM class.

As the group models use flask-sqlalchemy however, the functions in this
module should be called from within a Flask application context.
"""

from sqlalchemy.exc import IntegrityError
import collections
import datetime
import typing
import flask
from .. import db
from ..models import groups
from .users import get_user
from .security_tokens import generate_token
from .notifications import create_notification_for_being_invited_to_a_group
from . import errors


# group names are limited to this (semi-arbitrary) length
MAX_GROUP_NAME_LENGTH = 100


class Group(collections.namedtuple('Group', ['id', 'name', 'description'])):
    """
    This class provides an immutable wrapper around models.groups.Group.
    """

    def __new__(cls, id: int, name: str, description: str):
        self = super(Group, cls).__new__(cls, id, name, description)
        return self

    @classmethod
    def from_database(cls, group: groups.Group) -> 'Group':
        return Group(id=group.id, name=group.name, description=group.description)


class GroupInvitation(collections.namedtuple('GroupInvitation', ['id', 'group_id', 'user_id', 'inviter_id', 'utc_datetime', 'accepted'])):
    """
    This class provides an immutable wrapper around models.groups.GroupInvitation.
    """

    def __new__(cls, id: int, group_id: int, user_id: int, inviter_id: int, utc_datetime: datetime.datetime, accepted: bool):
        self = super(GroupInvitation, cls).__new__(cls, id, group_id, user_id, inviter_id, utc_datetime, accepted)
        return self

    @classmethod
    def from_database(cls, group_invitation: groups.GroupInvitation) -> 'GroupInvitation':
        return GroupInvitation(
            id=group_invitation.id,
            group_id=group_invitation.group_id,
            user_id=group_invitation.user_id,
            inviter_id=group_invitation.inviter_id,
            utc_datetime=group_invitation.utc_datetime,
            accepted=group_invitation.accepted
        )

    @property
    def expired(self):
        expiration_datetime = self.utc_datetime + datetime.timedelta(seconds=flask.current_app.config['INVITATION_TIME_LIMIT'])
        return datetime.datetime.utcnow() >= expiration_datetime


def create_group(name: str, description: str, initial_user_id: int) -> Group:
    """
    Creates a new group with the given name and description and adds an
    initial user to it.

    :param name: the unique name of the group
    :param description: a (possibly empty) description for the group
    :param initial_user_id: the user ID of the initial group member
    :return: the newly created group
    :raise errors.InvalidGroupNameError: when the group name is empty or more
        than MAX_GROUP_NAME_LENGTH characters long
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.GroupAlreadyExistsError: when another group with the given
        name already exists
    """
    if not 1 <= len(name) <= MAX_GROUP_NAME_LENGTH:
        raise errors.InvalidGroupNameError()
    user = get_user(initial_user_id)
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
    return group


def update_group(group_id: int, name: str, description: str = '') -> None:
    """
    Updates the group's name and description.

    :param group_id: the ID of an existing group
    :param name: the new unique group name
    :param description: the new group description
    :raise errors.InvalidGroupNameError: when the group name is empty or more
        than MAX_GROUP_NAME_LENGTH characters long
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    :raise errors.GroupAlreadyExistsError: when another group with the given
        name already exists
    """
    if not 1 <= len(name) <= MAX_GROUP_NAME_LENGTH:
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
    """
    Deletes the given group, freeing up the name and removing all permissions
    that might have been granted to the group.

    This is also implicitly done when the last member leaves a group.

    :param group_id: the ID of an existing group
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    """
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    # group permissions and group default permissions will be deleted due to
    # ondelete = "CASCADE" in the model. No need to delete them manually here.
    db.session.delete(group)
    db.session.commit()


def get_group(group_id: int) -> Group:
    """
    Returns the group with the given ID.

    :param group_id: the ID of an existing group
    :return: the group
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    """
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    return Group.from_database(group)


def get_groups() -> typing.List[Group]:
    """
    Returns a list of all existing groups.

    :return: the list of groups
    """
    return [Group.from_database(group) for group in groups.Group.query.all()]


def get_group_member_ids(group_id: int) -> typing.List[int]:
    """
    Returns a list of the user IDs of all members of the group with the given
    group ID.

    :param group_id: the ID of an existing group
    :return: the member ID list
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    """
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    return [user.id for user in group.members]


def get_user_groups(user_id: int) -> typing.List[Group]:
    """
    Returns a list of the group IDs of all groups the user with the given
    user ID is a member of.

    :param group_id: the ID of an existing user
    :return: the member ID list
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    user = get_user(user_id)
    return [Group.from_database(group) for group in user.groups]


def invite_user_to_group(group_id: int, user_id: int, inviter_id: int) -> None:
    """
    Invite a user to a group.

    :param group_id: the ID of an existing group
    :param user_id: the ID of an existing user
    :param inviter_id: the ID of who invited this user to the group
    :raise errors.GroupDoesNotExistError: when no group with the given group
        ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        or inviter ID exists
    :raise errors.UserAlreadyMemberOfGroupError: when the user with the given
        user ID already is a member of this group
    """
    # ensure the inviter exists
    get_user(inviter_id)
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    user = get_user(user_id)
    if user in group.members:
        raise errors.UserAlreadyMemberOfGroupError()

    invitation = groups.GroupInvitation(
        group_id=group_id,
        user_id=user_id,
        inviter_id=inviter_id,
        utc_datetime=datetime.datetime.utcnow()
    )
    db.session.add(invitation)
    db.session.commit()
    token = generate_token(
        {
            'invitation_id': invitation.id,
            'user_id': user.id,
            'group_id': group_id
        },
        salt='invite_to_group',
        secret_key=flask.current_app.config['SECRET_KEY']
    )
    expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
    expiration_utc_datetime = datetime.datetime.utcnow() + datetime.timedelta(seconds=expiration_time_limit)
    confirmation_url = flask.url_for("frontend.group", group_id=group_id, token=token, _external=True)
    create_notification_for_being_invited_to_a_group(user_id, group_id, inviter_id, confirmation_url, expiration_utc_datetime)


def add_user_to_group(group_id: int, user_id: int) -> None:
    """
    Adds the user with the given user ID to the group with the given group ID.

    :param group_id: the ID of an existing group
    :param user_id: the ID of an existing user
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.UserAlreadyMemberOfGroupError: when the user is already
        a member of the group
    """
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    user = get_user(user_id)
    if user in group.members:
        raise errors.UserAlreadyMemberOfGroupError()
    group.members.append(user)
    invitations = get_group_invitations(
        group_id=group_id,
        user_id=user_id,
        include_expired_invitations=False,
        include_accepted_invitations=False
    )
    for invitation in invitations:
        invitation = groups.GroupInvitation.query.filter_by(id=invitation.id).first()
        invitation.accepted = True
        db.session.add(invitation)
    db.session.commit()


def remove_user_from_group(group_id: int, user_id: int) -> None:
    """
    Removes the user with the given user ID from the group with the given
    group ID.

    If there are no members left in the group, it is deleted and its name is
    freed up to be used again for a new group.

    :param group_id: the ID of an existing group
    :param user_id: the ID of an existing user
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.UserNotMemberOfGroupError: when the user is not a member of
        the group
    """
    group = groups.Group.query.get(group_id)
    if group is None:
        raise errors.GroupDoesNotExistError()
    user = get_user(user_id)
    if user not in group.members:
        raise errors.UserNotMemberOfGroupError()
    group.members.remove(user)
    if not group.members:
        db.session.delete(group)
    db.session.commit()


def get_group_invitations(
        group_id: int,
        user_id: typing.Optional[int] = None,
        include_accepted_invitations: bool = True,
        include_expired_invitations: bool = True
) -> typing.List[GroupInvitation]:
    """
    Get all (current) invitations for a user to join a group.

    :param group_id: the ID of an existing group
    :param user_id: the ID of an existing user or None
    :param include_accepted_invitations: whether or not to include invitations
        that have already been accepted by the user
    :param include_expired_invitations: whether or not to include invitations
        that have already expired
    :return: the list of group invitations
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    """
    group_invitations_query = groups.GroupInvitation.query.filter_by(group_id=group_id)
    if user_id is not None:
        group_invitations_query = group_invitations_query.filter_by(user_id=user_id)
    if not include_accepted_invitations:
        group_invitations_query = group_invitations_query.filter_by(accepted=False)
    if not include_expired_invitations:
        expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
        expired_invitation_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=expiration_time_limit)
        group_invitations_query = group_invitations_query.filter(groups.GroupInvitation.utc_datetime > expired_invitation_datetime)
    group_invitations = group_invitations_query.order_by(groups.GroupInvitation.utc_datetime).all()
    if not group_invitations:
        # ensure that a group with this ID exists
        get_group(group_id)
    return [
        GroupInvitation.from_database(group_invitation)
        for group_invitation in group_invitations
    ]


def get_group_invitation(invitation_id: int) -> GroupInvitation:
    """
    Get an existing invitation.

    :param invitation_id: the ID of an existing invitation
    :return: the invitation
    :raise errors.GroupInvitationDoesNotExistError: when no invitation with
        the given ID exists
    """
    invitation = groups.GroupInvitation.query.filter_by(id=invitation_id).first()
    if invitation is None:
        raise errors.GroupInvitationDoesNotExistError()
    return GroupInvitation.from_database(invitation)
