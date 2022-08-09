# coding: utf-8
"""

"""

import collections
import copy
import datetime
import typing

import flask
import flask_login
from flask_babel import gettext

from .components import get_component
from .. import db
from . import errors, settings
from .. models import users, UserType


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


class User(collections.namedtuple('User', ['id', 'name', 'email', 'type', 'is_admin', 'is_readonly', 'is_hidden', 'is_active', 'orcid', 'affiliation', 'role', 'extra_fields', 'fed_id', 'component_id', 'last_modified']), flask_login.UserMixin):
    """
    This class provides an immutable wrapper around models.users.User.
    """

    def __new__(
            cls,
            id: int,
            name: str,
            email: str,
            type: UserType,
            is_admin: bool,
            is_readonly: bool,
            is_hidden: bool,
            is_active: bool,
            orcid: str,
            affiliation: str,
            role: str,
            extra_fields: typing.Dict[str, typing.Any],
            fed_id: int,
            component_id: int,
            last_modified: datetime.datetime
    ):
        self = super(User, cls).__new__(
            cls,
            id,
            name,
            email,
            type,
            is_admin,
            is_readonly,
            is_hidden,
            is_active,
            orcid,
            affiliation,
            role,
            extra_fields,
            fed_id,
            component_id,
            last_modified
        )
        return self

    @classmethod
    def from_database(cls, user: users.User) -> 'User':
        return User(
            id=user.id,
            name=user.name,
            email=user.email,
            type=user.type,
            is_admin=user.is_admin,
            is_readonly=user.is_readonly,
            is_hidden=user.is_hidden,
            is_active=user.is_active,
            orcid=user.orcid,
            affiliation=user.affiliation,
            role=user.role,
            extra_fields=copy.deepcopy(user.extra_fields),
            fed_id=user.fed_id,
            component_id=user.component_id,
            last_modified=user.last_modified
        )

    @property
    def component(self):
        if self.component_id is None:
            return None
        return get_component(self.component_id)

    def get_id(self):
        return self.id

    def get_name(self, include_ref=False):
        if include_ref and self.component_id is not None:
            db_ref = ', #{} @ {}'.format(self.fed_id, self.component.get_name())
        else:
            db_ref = ''
        if self.name is None:
            return gettext('Imported User (#%(user_id)s%(db_ref)s)', user_id=self.id, db_ref=db_ref)
        else:
            return '{} (#{}{})'.format(self.name, self.id, db_ref)

    @property
    def has_admin_permissions(self) -> bool:
        """
        Return whether the user has administrator permissions.

        This is the case if the user is an admin and has admin permissions enabled in their settings.
        """
        if not self.is_admin:
            return False
        user_settings = settings.get_user_settings(self.id)
        return user_settings['USE_ADMIN_PERMISSIONS']

    @property
    def timezone(self):
        if flask.current_app.config['TIMEZONE']:
            return flask.current_app.config['TIMEZONE']
        return settings.get_user_settings(self.id)['TIMEZONE']


class AnonymousUser(flask_login.AnonymousUserMixin):
    @property
    def id(self) -> typing.Optional[int]:
        return self.get_id()

    @property
    def has_admin_permissions(self) -> bool:
        return False

    @property
    def timezone(self):
        if flask.current_app.config['TIMEZONE']:
            return flask.current_app.config['TIMEZONE']
        return None

    @property
    def is_readonly(self) -> bool:
        # anonymous users cannot change anything but are not specifically marked as readonly
        return False


class UserFederationAlias(collections.namedtuple('UserFederationAlias', ['user_id', 'component_id', 'name', 'use_real_name', 'email', 'use_real_email', 'orcid', 'use_real_orcid', 'affiliation', 'use_real_affiliation', 'role', 'use_real_role', 'extra_fields', 'last_modified'])):
    """
    This class provides an immutable wrapper around models.users.UserFederationAlias.
    """

    def __new__(
            cls,
            user_id: int,
            component_id: int,
            name: typing.Optional[str],
            use_real_name: bool,
            email: typing.Optional[str],
            use_real_email: bool,
            orcid: typing.Optional[str],
            use_real_orcid: bool,
            affiliation: typing.Optional[str],
            use_real_affiliation: bool,
            role: typing.Optional[str],
            use_real_role: bool,
            extra_fields: typing.Dict[str, typing.Any],
            last_modified: datetime.datetime
    ):
        self = super(UserFederationAlias, cls).__new__(
            cls,
            user_id,
            component_id,
            name,
            use_real_name,
            email,
            use_real_email,
            orcid,
            use_real_orcid,
            affiliation,
            use_real_affiliation,
            role,
            use_real_role,
            extra_fields,
            last_modified
        )
        return self

    @classmethod
    def from_database(cls, alias: users.UserFederationAlias) -> 'UserFederationAlias':
        if any([alias.use_real_name, alias.use_real_email, alias.use_real_orcid, alias.use_real_affiliation, alias.use_real_role]):
            user = get_user(alias.user_id)
            return UserFederationAlias(
                user_id=alias.user_id,
                component_id=alias.component_id,
                name=user.name if alias.use_real_name else alias.name,
                use_real_name=alias.use_real_name,
                email=user.email if alias.use_real_email else alias.email,
                use_real_email=alias.use_real_email,
                orcid=user.orcid if alias.use_real_orcid else alias.orcid,
                use_real_orcid=alias.use_real_orcid,
                affiliation=user.affiliation if alias.use_real_affiliation else alias.affiliation,
                use_real_affiliation=alias.use_real_affiliation,
                role=user.role if alias.use_real_role else alias.role,
                use_real_role=alias.use_real_role,
                extra_fields=copy.deepcopy(alias.extra_fields),
                last_modified=alias.last_modified
            )
        else:
            return UserFederationAlias(
                user_id=alias.user_id,
                component_id=alias.component_id,
                name=alias.name,
                use_real_name=alias.use_real_name,
                email=alias.email,
                use_real_email=alias.use_real_email,
                orcid=alias.orcid,
                use_real_orcid=alias.use_real_orcid,
                affiliation=alias.affiliation,
                use_real_affiliation=alias.use_real_affiliation,
                role=alias.role,
                use_real_role=alias.use_real_role,
                extra_fields=copy.deepcopy(alias.extra_fields),
                last_modified=alias.last_modified
            )


def get_user(user_id: int, component_id: typing.Optional[int] = None) -> User:
    return User.from_database(get_mutable_user(user_id, component_id))


def get_mutable_user(user_id: int, component_id: typing.Optional[int] = None) -> users.User:
    """
    Get the mutable user instance to perform changes in the database on.

    :param user_id: the user ID of an existing user
    :param component_id: the ID of an existing component, or None
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    if user_id is None:
        raise TypeError("user_id must be int")
    if component_id is None or component_id == 0:
        user = users.User.query.get(user_id)
    else:
        user = users.User.query.filter_by(fed_id=user_id, component_id=component_id).first()
    if user is None:
        if component_id is not None:
            get_component(component_id)
        raise errors.UserDoesNotExistError()
    return user


def update_user(user_id: int, **attributes: typing.Dict[str, typing.Any]) -> None:
    """
    Update one or multiple attributes of an existing user in the database.

    :param user_id: the user ID of an existing user
    :param attributes: a mapping of attribute names and values
    :raise AttributeError: when a non-existing attribute is set
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    user = get_mutable_user(user_id)
    for name in attributes:
        if name not in {
            'name',
            'email',
            'type',
            'is_admin',
            'is_readonly',
            'is_hidden',
            'is_active',
            'orcid',
            'affiliation',
            'role',
            'extra_fields',
            'fed_id',
            'component_id'
        }:
            raise AttributeError(f"'User' object has no attribute '{name}'")

    for name, value in attributes.items():
        setattr(user, name, value)
    user.last_modified = datetime.datetime.utcnow()
    db.session.add(user)
    db.session.commit()


def get_users(exclude_hidden: bool = False, order_by: typing.Optional[db.Column] = users.User.name, exclude_fed: bool = False) -> typing.List[User]:
    """
    Returns all users.

    :param exclude_hidden: whether or not to exclude hidden users
    :param order_by: Column to order the users by, or None
    :return: the list of users
    """
    user_query = users.User.query
    if exclude_hidden:
        user_query = user_query.filter_by(is_hidden=False)
    if order_by is not None:
        user_query = user_query.order_by(order_by)
    if exclude_fed:
        user_query = user_query.filter(users.User.type != UserType.FEDERATION_USER)
    return [
        User.from_database(user)
        for user in user_query.all()
    ]


def get_users_for_component(component_id: int, exclude_hidden: bool = False, order_by: typing.Optional[db.Column] = users.User.name):
    user_query = users.User.query.filter_by(component_id=component_id)
    if exclude_hidden:
        user_query = user_query.filter_by(is_hidden=False)
    if order_by is not None:
        user_query = user_query.order_by(order_by)
    return [
        User.from_database(user)
        for user in user_query.all()
    ]


def get_administrators() -> typing.List[User]:
    """
    Returns all current administrators.

    :return: the list of administrators
    """
    return [
        User.from_database(user)
        for user in users.User.query.filter_by(is_admin=True).all()
    ]


def get_users_by_name(name: str) -> typing.List[User]:
    """
    Return all users with a given name.

    :param name: the user name to search for
    :return: the list of users with this name
    """
    return [
        User.from_database(user)
        for user in users.User.query.filter_by(name=name).all()
    ]


def create_user(
        name: typing.Optional[str],
        email: typing.Optional[str],
        type: UserType,
        orcid: typing.Optional[str] = None,
        affiliation: typing.Optional[str] = None,
        role: typing.Optional[str] = None,
        extra_fields: typing.Optional[dict] = None,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None
) -> User:
    """
    Create a new user.

    This function cannot create a user as an administrator. To set whether or
    not a user is an administrator, use the set_administrator script or
    set_user_administrator function.

    :param name: the user's name
    :param email: the user's email address
    :param type: the user's type
    :return: the newly created user
    """

    if (component_id is None) != (fed_id is None) or (component_id is None and (name is None or email is None)):
        raise TypeError('Invalid parameter combination.')

    if component_id is not None:
        get_component(component_id)

    user = users.User(name=name, email=email, type=type, orcid=orcid, affiliation=affiliation, role=role, extra_fields=extra_fields, fed_id=fed_id, component_id=component_id, last_modified=datetime.datetime.utcnow())
    db.session.add(user)
    db.session.commit()
    return User.from_database(user)


def set_user_readonly(user_id: int, readonly: bool) -> None:
    """
    Set whether a user should be limited to READ permissions.

    :param user_id: the user ID of an existing user
    :param readonly: True, if the user should be read only, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    update_user(user_id, is_readonly=readonly)


def set_user_hidden(user_id: int, hidden: bool) -> None:
    """
    Set whether a user should be hidden from user lists.

    :param user_id: the user ID of an existing user
    :param hidden: True, if the user should be hidden, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    update_user(user_id, is_hidden=hidden)


def set_user_active(user_id: int, active: bool) -> None:
    """
    Set whether a user should be allowed to sign in.

    :param user_id: the user ID of an existing user
    :param active: True, if the user should be active, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    update_user(user_id, is_active=active)


def set_user_administrator(user_id: int, is_admin: bool) -> None:
    """
    Set whether a user is an administrator.

    :param user_id: the user ID of an existing user
    :param is_admin: True, if the user is an administrator, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    update_user(user_id, is_admin=is_admin)


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


def get_user_alias(user_id: int, component_id: int) -> UserFederationAlias:
    """
    Get an existing user alias.

    :param user_id: the ID of an existing user
    :param component_id: the ID of an existing component
    :return: the user alias
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    :raise errors.ComponentDoesNotExistError: when no component with given ID exists
    :raise errors.UserAliasDoesNotExistError: when no alias with given IDs exists
    """
    alias = users.UserFederationAlias.query.get((user_id, component_id))
    if alias is None:
        get_user(user_id)
        get_component(component_id)
        raise errors.UserAliasDoesNotExistError()
    return UserFederationAlias.from_database(alias)


def get_user_aliases_for_user(user_id: int) -> typing.List[UserFederationAlias]:
    """
    Get all aliases for a user.

    :param user_id: the ID of an existing user
    :return: list of user aliases
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    """
    get_user(user_id)
    alias = users.UserFederationAlias.query.filter_by(user_id=user_id).all()
    return [UserFederationAlias.from_database(a) for a in alias]


def get_user_aliases_for_component(component_id: int, modified_since: typing.Optional[datetime.datetime] = None) -> typing.List[UserFederationAlias]:
    """
    Get all aliases for a component.

    :param component_id: the ID of an existing component
    :param modified_since: Only return aliases modified since modified_since. None to query every alias. (default: None)
    :return: list of user aliases
    :raise errors.ComponentDoesNotExistError: when no component with the given ID exists
    """
    get_component(component_id)
    if modified_since is None:
        alias = users.UserFederationAlias.query.filter_by(component_id=component_id).all()
    else:
        alias = users.UserFederationAlias.query.filter(
            db.or_(
                db.and_(
                    users.UserFederationAlias.component_id == component_id,
                    users.UserFederationAlias.last_modified >= modified_since
                ),
                db.and_(
                    db.or_(users.UserFederationAlias.use_real_name, users.UserFederationAlias.use_real_email, users.UserFederationAlias.use_real_orcid, users.UserFederationAlias.use_real_affiliation, users.UserFederationAlias.use_real_role),
                    users.User.last_modified >= modified_since
                )
            )
        ).all()
    return [UserFederationAlias.from_database(a) for a in alias]


def create_user_alias(
    user_id: int,
    component_id: int,
    name: typing.Optional[str] = None,
    use_real_name: bool = False,
    email: typing.Optional[str] = None,
    use_real_email: bool = False,
    orcid: typing.Optional[str] = None,
    use_real_orcid: bool = False,
    affiliation: typing.Optional[str] = None,
    use_real_affiliation: bool = False,
    role: typing.Optional[str] = None,
    use_real_role: bool = False
) -> UserFederationAlias:
    """
    Create a new user alias for a component.

    :param user_id: the ID of an existing user
    :param component_id:  the ID of an existing component
    :param name: the alias name
    :param use_real_name: boolean whether to use the name from the users' profile
    :param email: the alias email
    :param use_real_email: boolean whether to use the email from the users' profile
    :param orcid: the alias orcid
    :param use_real_orcid: boolean whether to use the orcid from the users' profile
    :param affiliation: the alias affiliation
    :param use_real_affiliation: boolean whether to use the affiliation from the users' profile
    :param role: the alias role
    :param use_real_role: boolean whether to use the role from the users' profile
    :return: the new created alias
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    :raise errors.ComponentDoesNotExistError: when no component with given ID exists
    :raise errors.UserAliasAlreadyExistsError: when an alias with given IDs already exists
    """
    alias = users.UserFederationAlias.query.get((user_id, component_id))
    if alias is not None:
        get_user(user_id)
        get_component(component_id)
        raise errors.UserAliasAlreadyExistsError()
    if use_real_name:
        name = None
    if use_real_email:
        email = None
    if use_real_orcid:
        orcid = None
    if use_real_affiliation:
        affiliation = None
    if use_real_role:
        role = None
    alias = users.UserFederationAlias(user_id, component_id, name, use_real_name, email, use_real_email, orcid, use_real_orcid, affiliation, use_real_affiliation, role, use_real_role, {})
    db.session.add(alias)
    db.session.commit()
    return UserFederationAlias.from_database(alias)


def update_user_alias(
    user_id: int,
    component_id: int,
    name: typing.Optional[str] = None,
    use_real_name: bool = False,
    email: typing.Optional[str] = None,
    use_real_email: bool = False,
    orcid: typing.Optional[str] = None,
    use_real_orcid: bool = False,
    affiliation: typing.Optional[str] = None,
    use_real_affiliation: bool = False,
    role: typing.Optional[str] = None,
    use_real_role: bool = False
) -> None:
    """
    Update a users' alias for a component.

    :param user_id: the ID of an existing user
    :param component_id:  the ID of an existing component
    :param name: the alias name
    :param use_real_name: boolean whether to use the name from the users' profile
    :param email: the alias email
    :param use_real_email: boolean whether to use the email from the users' profile
    :param orcid: the alias orcid
    :param use_real_orcid: boolean whether to use the orcid from the users' profile
    :param affiliation: the alias affiliation
    :param use_real_affiliation: boolean whether to use the affiliation from the users' profile
    :param role: the alias role
    :param use_real_role: boolean whether to use the role from the users' profile
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    :raise errors.ComponentDoesNotExistError: when no component with given ID exists
    :raise errors.UserAliasDoesNotExistError: when no alias with given IDs exists
    """
    alias = users.UserFederationAlias.query.get((user_id, component_id))
    if alias is None:
        get_user(user_id)
        get_component(component_id)
        raise errors.UserAliasDoesNotExistError()
    if use_real_name:
        name = None
    if use_real_email:
        email = None
    if use_real_orcid:
        orcid = None
    if use_real_affiliation:
        affiliation = None
    if use_real_role:
        role = None
    alias.name = name
    alias.use_real_name = use_real_name
    alias.email = email
    alias.use_real_email = use_real_email
    alias.orcid = orcid
    alias.use_real_orcid = use_real_orcid
    alias.affiliation = affiliation
    alias.use_real_affiliation = use_real_affiliation
    alias.role = role
    alias.use_real_role = use_real_role
    alias.last_modified = datetime.datetime.utcnow()
    db.session.add(alias)
    db.session.commit()


def delete_user_alias(user_id: int, component_id: int) -> None:
    """
    Delete a user alias.

    :param user_id: the ID of an existing user
    :param component_id:  the ID of an existing component
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    :raise errors.ComponentDoesNotExistError: when no component with given ID exists
    :raise errors.UserAliasDoesNotExistError: when no alias with given IDs exists
    """
    alias = users.UserFederationAlias.query.get((user_id, component_id))
    if alias is None:
        get_user(user_id)
        get_component(component_id)
        raise errors.UserAliasDoesNotExistError()
    db.session.delete(alias)
    db.session.commit()
